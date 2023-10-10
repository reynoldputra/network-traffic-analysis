import argparse
import json
import logging
import os
import pickle
import re
import sys
from collections import Counter, defaultdict, deque
from collections import defaultdict, deque

import pyshark
import requests

from database.database import dbCreate, dbGet

cache_file = "cache.pkl"

def load_from_cache(cache_key):
    if not os.path.exists(cache_file):
        return None

    with open(cache_file, "rb") as f:
        cache = pickle.load(f)
        return cache.get(cache_key)

def save_to_cache(cache_key, data):
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            cache = pickle.load(f)
    else:
        cache = {}

    with open(cache_file, "wb") as f:
        cache[cache_key] = data
        pickle.dump(cache, f)

def fetch_data(source_name, source_url):
    cached_data = load_from_cache(source_name)
    if cached_data is not None:
        logging.info(f"Loaded {source_name} from cache")
        return cached_data

    try:
        response = requests.get(source_url)
        response.raise_for_status()
        data = response.text
        save_to_cache(source_name, data)
        logging.info(f"Successfully fetched {source_name}")
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching {source_name}: {e}")
        return ""

def fetch_sources(sources):
    fetched_items = {}

    for source in sources:
        source_name = source["name"]
        source_url = source["url"]
        data = fetch_data(source_name, source_url)
        if data is not None:
            fetched_items[source_name] = set(data.splitlines())
            logging.info(f"Successfully fetched {source_name}")

    return fetched_items

def load_malicious_definitions(json_file):
    with open(json_file, "r") as f:
        definitions = json.load(f)
    return definitions

def update_definitions(malicious_definitions):
    malicious_data = {
        'ip': fetch_sources(malicious_definitions["ip_sources"]),
        'domain': fetch_sources(malicious_definitions["domain_sources"]),
        'signature': fetch_sources(malicious_definitions["signature_sources"]),
    }
    return malicious_data

def extract_domain(packet):
    domain = ''

    if 'dns' in packet:
        try:
            domain = packet.dns.qry_name
        except AttributeError:
            pass

    return domain

def process_signature_file(file_content):
    lines = file_content.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("alert"):
            signatures.append(line)

signatures = []

def detect_malware_delivery(packet, malicious_definitions):
    if not hasattr(packet, 'tcp') or not hasattr(packet.tcp, 'payload'):
        return False

    payload = packet.tcp.payload

    payload_str = ''.join([chr(int(payload[i:i+2], 16)) for i in range(0, len(payload), 2)])
    payload_clean = re.sub(r'[^\x20-\x7E]', '', payload_str)

    for source_name, signatures in malicious_definitions['signatures'].items():
        for signature in signatures:
            if re.search(signature, payload_clean):
                return f"Malware delivery detected from {source_name}: {signature}"
    return ""

def extract_dns_query(packet):
    if 'DNS' in packet and hasattr(packet.dns, 'qry_name') and packet.dns.qry_name:
        return packet.dns.qry_name.lower()
    return None

def detect_phishing_attempts(packet, malicious_definitions):
    dns_query = extract_dns_query(packet)

    if dns_query:
        for source_name, domain_list in malicious_definitions['domain'].items():
            if dns_query in domain_list:
                logging.info(f"Phishing attempt detected from {source_name}: {dns_query}")
                return True
    return False

login_attempts = defaultdict(list)
login_attempt_counters = Counter()

def detect_brute_force_attacks(packet, malicious_definitions, threshold=5, time_window=60):
    if 'TCP' in packet and hasattr(packet.tcp, 'flags'):
        src_ip = packet.ip.src
        dst_ip = packet.ip.dst
        timestamp = float(packet.sniff_timestamp)

        if packet.tcp.flags_rst == '1':
            login_attempts[(src_ip, dst_ip)].append(timestamp)

            login_attempts[(src_ip, dst_ip)] = [t for t in login_attempts[(src_ip, dst_ip)] if timestamp - t <= time_window]

            login_attempt_counters[(src_ip, dst_ip)] = len(login_attempts[(src_ip, dst_ip)])

            if login_attempt_counters[(src_ip, dst_ip)] >= threshold:
                logging.info(f"Brute force attack detected: {src_ip} -> {dst_ip}")
                return True

    return False

packet_counts = defaultdict(int)
packet_timestamps = defaultdict(float)


src_ip_counter = defaultdict(int)
dst_ip_counter = defaultdict(int)
window_size = 10
packet_window = deque(maxlen=window_size)

def detect_ddos_attacks(packet, window_size=10, threshold=100):
    global src_ip_counter, dst_ip_counter, packet_window

    src_ip = packet.IP.src  
    dst_ip = packet.IP.dst  
    timestamp = float(packet.sniff_timestamp)  

    while packet_window and timestamp - packet_window[0]['timestamp'] > window_size:
        expired_packet = packet_window.popleft()
        src_ip_counter[expired_packet['src_ip']] -= 1
        dst_ip_counter[expired_packet['dst_ip']] -= 1

    packet_window.append(packet)
    src_ip_counter[src_ip] += 1
    dst_ip_counter[dst_ip] += 1

    if src_ip_counter[src_ip] > threshold or dst_ip_counter[dst_ip] > threshold:
        logging.info(f"Possible DDoS attack detected! src_ip: {src_ip}, dst_ip: {dst_ip}, timestamp: {timestamp}")
        return True

    return False


def detect_malicious_patterns(packet_stream):
    patterns = [
        (re.compile(r'GET /(?:\.\./\w+)+', re.IGNORECASE), 'Directory Traversal Attack'),
        (re.compile(r'(?:\%3C|\x3C)[\w\s]*?(?:\%2F|\x2F)[\w\s]*?(?:\%3E|\x3E)', re.IGNORECASE), 'Cross-site Scripting (XSS) Attack'),
        (re.compile(r'[\w\.\-_]+@[\w\.\-_]+\.\w+', re.IGNORECASE), 'Email Address Harvesting'),
        (re.compile(r'(?:\%27|\x27|\'|\%2527|%5C)(?:\%45|\x45|E)(?:\%58|\x58|X)(?:\%50|\x50|R)', re.IGNORECASE), 'SQL Injection Attack')
    ]

    for packet in packet_stream:
        payload = packet['payload']
        
        for pattern, attack_name in patterns:
            if pattern.search(payload):
                logging.info(f"Malicious pattern detected! Attack type: {attack_name}, Packet: {packet}")
                break

def detect_cc_traffic(packet, malicious_definitions):
    if 'DNS' in packet:
        if hasattr(packet.dns, 'qry_name'):
            domain = packet.dns.qry_name

            for source_name, domain_list in malicious_definitions['domains'].items():
                if domain in domain_list:
                    logging.info(f"C&C traffic detected from {source_name}: {domain}")
                    return True

            dga_pattern = re.compile(r'^[a-z0-9]{10,}\.[a-z]{2,3}$', re.IGNORECASE)
            if dga_pattern.match(domain):
                logging.info(f"Suspicious DGA-like domain detected: {domain}")
                return True

    if 'HTTP' in packet:
        if hasattr(packet.http, 'request_uri'):
            uri = packet.http.request_uri
            suspicious_uri_pattern = re.compile(r'^/.*\.php\?.*=[a-zA-Z0-9]{20,}$')
            if suspicious_uri_pattern.match(uri):
                logging.info(f"Suspicious HTTP C&C traffic detected: {uri}")
                return True

    if 'IRC' in packet:
        if hasattr(packet.irc, 'request'):
            irc_request = packet.irc.request.lower()
            suspicious_irc_pattern = re.compile(r'^eval [a-zA-Z0-9]{20,}$')
            if suspicious_irc_pattern.match(irc_request):
                logging.info(f"Suspicious IRC C&C traffic detected: {irc_request}")
                return True

    return False

def is_hex_string(s):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False

def is_malicious_packet(packet, malicious_definitions):
    try:
        if not hasattr(packet, 'IP'):
            return False

        src_ip = packet.IP.src
        src_port = ""
        dst_ip = packet.IP.dst
        dst_port = packet.transport_layer.dstport
        timestamp = packet.sniff_timestamp

        if 'ip' in malicious_definitions:
            for source_name, ip_list in malicious_definitions['ip'].items():
                if src_ip in ip_list or dst_ip in ip_list:
                    write_log(timestamp, src_ip, src_port, dst_ip, dst_port, "Bad IP" )
                    logging.info(f"Malicious packet detected from {source_name}: {src_ip} -> {dst_ip}")
                    return True

        domain = extract_domain(packet)
        if domain and any(domain in domain_list for domain_list in malicious_definitions['domain'].values()):
            write_log(timestamp, src_ip, src_port, dst_ip, dst_port, "Domain Match" )
            logging.info(f"Malicious packet detected (domain match): {domain}")
            return True

        if 'TCP' in packet or 'UDP' in packet:
            payload = packet.tcp.payload if 'TCP' in packet else packet.udp.payload if 'UDP' in packet else ''

            if payload and is_hex_string(payload.replace(':', '')):
                payload_int = int(payload.replace(':', ''), 16)
                # Perform further processing with payload_int

            if 'signature' in malicious_definitions:
                for category, signatures in malicious_definitions['signature'].items():
                    for signature in signatures:
                        if isinstance(signature, str):
                            pattern = re.compile(signature, re.IGNORECASE)
                        else:
                            pattern = signature

                        if pattern.search(payload):
                            return True, category

        malware_delivery = detect_malware_delivery(packet, malicious_definitions)
        if malware_delivery:
            write_log(timestamp, src_ip, src_port, dst_ip, dst_port, "Malware Delivery" )
            logging.info(malware_delivery)
            return True

        if detect_phishing_attempts(packet, malicious_definitions):
            write_log(timestamp, src_ip, src_port, dst_ip, dst_port, "Phising" )
            logging.info("Phishing attempt detected")
            return True

        if detect_brute_force_attacks(packet, malicious_definitions):
            write_log(timestamp, src_ip, src_port, dst_ip, dst_port, "Brute Force" )
            logging.info("Brute force attack detected")
            return True

        if detect_ddos_attacks(packet, malicious_definitions):
            write_log(timestamp, src_ip, src_port, dst_ip, dst_port, "DDOS" )
            logging.info("DDoS attack detected")
            return True

        if detect_cc_traffic(packet, malicious_definitions):
            write_log(timestamp, src_ip, src_port, dst_ip, dst_port, "C&C Traffix" )
            logging.info("C&C traffic detected")
            return True

    except Exception as e:
        _, _, tb = sys.exc_info()
        if tb is not None:
            logging.error(f"Error while processing packet at line {tb.tb_lineno}: {e}")
        else:
            logging.error(f"Error while processing packet: {e}")
        return False

    return False


def write_log(timestamp, src_ip, src_port, dest_ip, dest_port, detail):
    insert_query = '''
        INSERT INTO log (timestamp, src, dst, detail)
        VALUES (?, ?, ?, ?)
    '''
    data = (timestamp, src_ip, src_port, dest_ip, dest_port, detail)
    dbCreate(insert_query, data)

            
if __name__ == "__main__":
    try:
        table_exists = dbGet("SELECT name FROM sqlite_master WHERE type='table' AND name='log'")

        create_table_query = '''
            CREATE TABLE log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                src_ip TEXT,
                src_port TEXT,
                dst_ip TEXT,
                dst_port TEXT,
                detail TEXT
            )
        '''
        if not table_exists:
            dbCreate(create_table_query)

        # capture = pyshark.LiveCapture('eth0')

        # for packet in capture:
        #     if hasattr(packet, 'ip'):
        #         src_ip = packet.ip.src
        #         dst_ip = packet.ip.dst
        #         timestamp = float(packet.sniff_timestamp)

        #         packet_info = {
        #             'src_ip': src_ip,
        #             'dst_ip': dst_ip,
        #             'timestamp': timestamp
        #         }

        #         print(packet_info)

        #         malicious_definitions = load_malicious_definitions("../data/malicious.json")
        #         malicious_data = update_definitions(malicious_definitions)
        #         if is_malicious_packet(packet, malicious_data):
        #             logging.info("Malicious packet detected: %s", packet)
        #             malicious_packet_detected = True
    except Exception as e:
        logging.error(f"Error while analyzing pcap file: {e}") 
