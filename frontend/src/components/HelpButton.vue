<template>
  <Button
    :icon="icon"
    :label="label"
    :severity="severity"
    :outlined="outlined"
    :text="text"
    @click="openHelp"
    :class="['help-button', customClass]"
    v-tooltip.left="tooltip"
  />
</template>

<script setup lang="ts">
interface Props {
  helpType: 'user' | 'admin' | 'developer' | 'quick-start'
  section?: string
  icon?: string
  label?: string
  severity?: string
  outlined?: boolean
  text?: boolean
  customClass?: string
  tooltip?: string
}

const props = withDefaults(defineProps<Props>(), {
  icon: 'pi pi-question-circle',
  label: '',
  severity: 'help',
  outlined: false,
  text: true,
  customClass: '',
  tooltip: 'View help documentation'
})

const helpUrls: Record<string, string> = {
  'user': 'https://github.com/dgalluzzo26/source2target/blob/main/docs/USER_GUIDE.md',
  'admin': 'https://github.com/dgalluzzo26/source2target/blob/main/docs/ADMIN_GUIDE.md',
  'developer': 'https://github.com/dgalluzzo26/source2target/blob/main/docs/DEVELOPER_GUIDE.md',
  'quick-start': 'https://github.com/dgalluzzo26/source2target/blob/main/docs/QUICK_START.md'
}

const openHelp = () => {
  let url = helpUrls[props.helpType]
  
  // Add section anchor if provided
  if (props.section) {
    const anchor = props.section.toLowerCase().replace(/\s+/g, '-')
    url += `#${anchor}`
  }
  
  window.open(url, '_blank')
}
</script>

<style scoped>
.help-button {
  margin-left: 0.5rem;
}
</style>

