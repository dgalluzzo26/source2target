/**
 * Vue Application Entry Point
 * 
 * Initializes and configures the Vue 3 application with:
 * - Pinia state management
 * - Vue Router for navigation
 * - PrimeVue UI component library with Aura theme
 * - Global component registration for commonly used PrimeVue components
 * - Custom Gainwell theme styles
 * 
 * This file is the first JavaScript file loaded by the application.
 * It sets up all global plugins, components, and directives before
 * mounting the root App component to the DOM.
 * 
 * @module main
 */

// Global styles (order matters - theme overrides base styles)
import './assets/main.css'
import './assets/gainwell-theme.css'

// Vue core and plugins
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'

// Root component and router
import App from './App.vue'
import router from './router'

// PrimeIcons CSS (icon font)
import 'primeicons/primeicons.css'

// PrimeVue Components (imported for global registration)
import Button from 'primevue/button'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Dialog from 'primevue/dialog'
import FileUpload from 'primevue/fileupload'
import Textarea from 'primevue/textarea'
import InputNumber from 'primevue/inputnumber'
import Dropdown from 'primevue/dropdown'
import Checkbox from 'primevue/checkbox'
import Accordion from 'primevue/accordion'
import AccordionTab from 'primevue/accordiontab'
import Divider from 'primevue/divider'
import Message from 'primevue/message'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Tooltip from 'primevue/tooltip'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import Steps from 'primevue/steps'
import RadioButton from 'primevue/radiobutton'

// Create Vue application instance
const app = createApp(App)

// Install plugins
app.use(createPinia())  // State management
app.use(router)         // Routing

// Configure PrimeVue with Aura theme
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      prefix: 'p',                  // Component prefix (e.g., p-button)
      darkModeSelector: '.p-dark',  // Dark mode CSS class
      cssLayer: false               // Don't use CSS layers (for compatibility)
    }
  }
})

// Install PrimeVue services for toast notifications and confirmations
app.use(ToastService)
app.use(ConfirmationService)

// Register PrimeVue components globally for use in all templates
// This avoids needing to import them in every component that uses them
app.component('Button', Button)
app.component('Card', Card)
app.component('DataTable', DataTable)
app.component('Column', Column)
app.component('InputText', InputText)
app.component('Tag', Tag)
app.component('TabView', TabView)
app.component('TabPanel', TabPanel)
app.component('Dialog', Dialog)
app.component('FileUpload', FileUpload)
app.component('Textarea', Textarea)
app.component('InputNumber', InputNumber)
app.component('Dropdown', Dropdown)
app.component('Checkbox', Checkbox)
app.component('Accordion', Accordion)
app.component('AccordionTab', AccordionTab)
app.component('Divider', Divider)
app.component('Message', Message)
app.component('IconField', IconField)
app.component('InputIcon', InputIcon)
app.component('Toast', Toast)
app.component('ConfirmDialog', ConfirmDialog)
app.component('Steps', Steps)
app.component('RadioButton', RadioButton)

// Register PrimeVue directives globally
app.directive('tooltip', Tooltip)

// Mount the application to the DOM
app.mount('#app')
