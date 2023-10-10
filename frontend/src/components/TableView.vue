<script setup>
  import axios from 'axios';

  const fetchData = async () => {
    try {
      const response = await axios.get('http://localhost:5001/data'); 
      const data = response.data; 
    
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };
  onMounted(() => {
    fetchData();
  });

  const data = [
    {
      timestamp: 'fadfads',
      src_ip: 'fadfads',
      src_port: 'fadfads',
      dst_ip: 'fadfads',
      dst_port: 'fadfads',
      detail: 'fadfads',
    },
  ];
</script>

<template>
  <div class="bg-[#FAF0F0] w-[1260px] mx-[117px] my-[10px] text-[#1F3C9C]">
    <div class="grid grid-cols-6 gap-4">
        <div class="font-bold">Timestamp</div>
        <div class="font-bold">Source IP</div>
        <div class="font-bold">Source Port</div>
        <div class="font-bold">Destination IP</div>
        <div class="font-bold">Destination PORT</div>
        <div class="font-bold">Detail</div>
        <template v-for="(d) in data">
          <div >
            {{ d.timestamp }}
          </div>
           <div>
            {{ d.src_ip }}
          </div>
           <div>
            {{ d.src_port }}
          </div>
           <div>
            {{ d.dst_ip }}
          </div>
           <div>
            {{ d.dst_port }}
          </div>
          <div>
            {{ d.detail }}
          </div>
        </template>
    </div>
  </div>
</template>
