<template>
  <Dialog
    v-model:visible="isVisible"
    modal
    header="Provide Feedback"
    :style="{ width: '600px' }"
    :closable="true"
  >
    <div class="feedback-content">
      <Message severity="info" :closable="false">
        Your feedback helps improve future AI suggestions!
      </Message>

      <div class="feedback-section">
        <h4>How was this suggestion?</h4>
        <div class="feedback-buttons">
          <Button
            label="👍 Accepted"
            icon="pi pi-check"
            severity="success"
            :outlined="feedbackStatus !== 'ACCEPTED'"
            @click="feedbackStatus = 'ACCEPTED'"
          />
          <Button
            label="👎 Rejected"
            icon="pi pi-times"
            severity="danger"
            :outlined="feedbackStatus !== 'REJECTED'"
            @click="feedbackStatus = 'REJECTED'"
          />
        </div>
      </div>

      <div v-if="feedbackStatus === 'REJECTED'" class="comment-section">
        <label for="feedback-comment">Why did you reject this suggestion? (Optional)</label>
        <Textarea
          id="feedback-comment"
          v-model="userComment"
          rows="4"
          placeholder="e.g., Field names don't match, Wrong data type, etc."
          class="w-full"
        />
      </div>
    </div>

    <template #footer>
      <Button label="Cancel" icon="pi pi-times" @click="handleCancel" text />
      <Button 
        label="Submit Feedback" 
        icon="pi pi-send" 
        @click="handleSubmit"
        :disabled="!feedbackStatus"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Message from 'primevue/message'

interface Props {
  visible: boolean
  sourceField?: string
  targetField?: string
}

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'feedback-submitted', feedback: {
    status: string
    comment?: string
  }): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const feedbackStatus = ref<'ACCEPTED' | 'REJECTED' | null>(null)
const userComment = ref('')

const isVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

function handleSubmit() {
  if (!feedbackStatus.value) return

  emit('feedback-submitted', {
    status: feedbackStatus.value,
    comment: userComment.value || undefined
  })

  // Reset and close
  feedbackStatus.value = null
  userComment.value = ''
  isVisible.value = false
}

function handleCancel() {
  feedbackStatus.value = null
  userComment.value = ''
  isVisible.value = false
}
</script>

<style scoped>
.feedback-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.feedback-section h4 {
  margin: 0 0 0.75rem 0;
  color: var(--text-color);
}

.feedback-buttons {
  display: flex;
  gap: 1rem;
}

.feedback-buttons button {
  flex: 1;
}

.comment-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.comment-section label {
  font-weight: 600;
  color: var(--text-color);
}
</style>

