<script setup>
const times = ["08:00 AM", "09:15 AM", "10:30 AM", "11:45 AM"];
const logs = ["Log 1", "Log 2", "Log 3", "Log 4"];
const threatLevels = ["Low", "Medium", "High"];
const detail = ["Detail 1", "Detail 2", "Detail 3"];
</script>

<template>
  <div class="bg-[#FAF0F0] w-[1260px] mx-[117px] my-[10px] text-[#1F3C9C]">
    <div class="grid grid-cols-4 gap-4">
      <div>
        <div class="font-bold">Timestamp</div>
        <div v-for="(time, index) in times" :key="'time-' + index" class="py-2">
          {{ time }}
        </div>
      </div>

      <div>
        <div class="font-bold">Log</div>
        <div v-for="(log, index) in logs" :key="'log-' + index" class="py-2">
          {{ log }}
        </div>
      </div>

      <div>
        <div class="font-bold">Threats Level</div>
        <div
          v-for="(threatLevel, index) in threatLevels"
          :key="'threat-' + index"
          class="py-2"
        >
          {{ threatLevel }}
        </div>
      </div>

      <div>
        <div class="font-bold">Detail</div>
        <div
          v-for="(detailItem, index) in detail"
          :key="'detail-' + index"
          class="py-2"
        >
          {{ detailItem }}
        </div>
      </div>
    </div>
  </div>
</template>
