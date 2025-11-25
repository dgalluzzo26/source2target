<template>
  <Dialog
    v-model:visible="isVisible"
    modal
    :style="{ width: '800px' }"
    :closable="true"
    class="feedback-dialog"
  >
    <template #header>
      <div class="feedback-header">
        <i class="pi pi-comment header-icon"></i>
        <h2>Provide Feedback on AI Suggestion</h2>
      </div>
    </template>

    <div class="feedback-content">
      <Message severity="info" :closable="false">
        <strong>Your feedback helps improve future AI suggestions!</strong>
        <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">Let us know if this suggestion was helpful or needs improvement.</p>
      </Message>

      <!-- Mapping Details -->
      <div class="mapping-details">
        <h4><i class="pi pi-arrow-right-arrow-left"></i> Mapping Details</h4>
        <div class="mapping-info">
          <div class="mapping-field">
            <label>Source Field:</label>
            <span class="field-name">{{ sourceField || 'Multiple fields selected' }}</span>
          </div>
          <div class="mapping-arrow">
            <i class="pi pi-arrow-right"></i>
          </div>
          <div class="mapping-field">
            <label>Target Field:</label>
            <span class="field-name">{{ targetField || 'Not specified' }}</span>
          </div>
        </div>
      </div>

      <!-- Feedback Selection -->
      <div class="feedback-section">
        <h4><i class="pi pi-star"></i> How was this suggestion?</h4>
        <div class="feedback-buttons">
          <Button
            label="Accepted - Good Match"
            icon="pi pi-check"
            severity="success"
            :outlined="feedbackStatus !== 'ACCEPTED'"
            @click="feedbackStatus = 'ACCEPTED'"
            class="feedback-button"
          />
          <Button
            label="Rejected - Poor Match"
            icon="pi pi-times"
            severity="danger"
            :outlined="feedbackStatus !== 'REJECTED'"
            @click="feedbackStatus = 'REJECTED'"
            class="feedback-button"
          />
        </div>
      </div>

      <!-- Comment Section (shown for both ACCEPTED and REJECTED) -->
      <div v-if="feedbackStatus" class="comment-section">
        <label for="feedback-comment">
          <i class="pi pi-comment"></i>
          {{ feedbackStatus === 'REJECTED' ? 'Why did you reject this suggestion?' : 'Additional comments (Optional)' }}
        </label>
        <Textarea
          id="feedback-comment"
          v-model="userComment"
          rows="6"
          :placeholder="feedbackStatus === 'REJECTED' 
            ? 'e.g., Field names don\'t match, Wrong data type, Incorrect semantic meaning, etc.' 
            : 'e.g., This was helpful because..., Could be improved by..., etc.'"
          class="w-full"
          autoResize
        />
      </div>
    </div>

    <template #footer>
      <div class="footer-buttons">
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="handleCancel" 
          text 
          severity="secondary"
        />
        <Button 
          label="Submit Feedback" 
          icon="pi pi-send" 
          @click="handleSubmit"
          :disabled="!feedbackStatus"
          severity="primary"
        />
      </div>
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
.feedback-dialog :deep(.p-dialog-header) {
  background: linear-gradient(135deg, #4a5568, #38a169);
  color: white;
  padding: 1.5rem;
  border-radius: 10px 10px 0 0;
}

.feedback-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: white;
}

.feedback-header .header-icon {
  font-size: 1.5rem;
}

.feedback-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: white;
}

.feedback-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  padding: 1rem 0;
}

/* Mapping Details Section */
.mapping-details {
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  padding: 1.5rem;
  border-radius: 8px;
  border-left: 4px solid #38a169;
}

.mapping-details h4 {
  margin: 0 0 1rem 0;
  color: #4a5568;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.mapping-info {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 1rem;
  align-items: center;
}

.mapping-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.mapping-field label {
  font-size: 0.85rem;
  color: #6c757d;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.mapping-field .field-name {
  padding: 0.75rem;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  font-size: 0.95rem;
  color: #212529;
  font-weight: 500;
}

.mapping-arrow {
  color: #38a169;
  font-size: 1.5rem;
  margin-top: 1.5rem;
}

/* Feedback Section */
.feedback-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.feedback-section h4 {
  margin: 0;
  color: #4a5568;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.feedback-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.feedback-button {
  padding: 1rem !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
}

/* Comment Section */
.comment-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
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
  color: #4a5568;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.comment-section :deep(.p-inputtextarea) {
  font-size: 0.95rem;
  line-height: 1.6;
  border: 2px solid #dee2e6;
  border-radius: 6px;
  padding: 0.75rem;
}

.comment-section :deep(.p-inputtextarea:focus) {
  border-color: #38a169;
  box-shadow: 0 0 0 0.2rem rgba(56, 161, 105, 0.25);
}

/* Footer */
.footer-buttons {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  width: 100%;
}

/* Enhanced Message */
.feedback-content :deep(.p-message) {
  border-left: 4px solid #3b82f6;
}

.feedback-content :deep(.p-message .p-message-wrapper) {
  padding: 1rem;
}
</style>

