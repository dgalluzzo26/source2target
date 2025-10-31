<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView />
</template>

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--gainwell-bg-secondary);
  color: var(--gainwell-text-primary);
}

#app {
  min-height: 100vh;
  width: 100%;
}
</style>

