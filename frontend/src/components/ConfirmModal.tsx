import { Show } from 'solid-js';

interface ConfirmModalProps {
  show: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
  type?: 'danger' | 'info' | 'warning';
}

export function ConfirmModal(props: ConfirmModalProps) {
  const typeClasses = () => {
    switch (props.type) {
      case 'danger':
        return {
          icon: 'bg-red-100 text-red-600',
          button: 'bg-red-600 hover:bg-red-700 focus:ring-red-500 shadow-red-200',
          border: 'border-red-100',
        };
      case 'warning':
        return {
          icon: 'bg-amber-100 text-amber-600',
          button: 'bg-amber-600 hover:bg-amber-700 focus:ring-amber-500 shadow-amber-200',
          border: 'border-amber-100',
        };
      default:
        return {
          icon: 'bg-primary/10 text-primary',
          button: 'bg-primary hover:bg-primary-dark focus:ring-primary shadow-primary/20',
          border: 'border-primary/10',
        };
    }
  };

  return (
    <Show when={props.show}>
      <div class="fixed inset-0 z-[300] flex items-center justify-center p-4 sm:p-6">
        {/* Backdrop */}
        <div 
          class="absolute inset-0 bg-black/40 backdrop-blur-[4px] transition-opacity animate-in fade-in duration-300"
          onClick={props.onCancel}
        />
        
        {/* Modal Content */}
        <div class="relative w-full max-w-md bg-white rounded-3xl shadow-2xl border border-gray-100 overflow-hidden transform transition-all animate-in zoom-in-95 duration-300">
          <div class="p-8">
            <div class="flex items-center gap-4 mb-6">
              <div class={`flex-shrink-0 w-12 h-12 rounded-2xl flex items-center justify-center ${typeClasses().icon}`}>
                <Show when={props.type === 'danger'} fallback={
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                }>
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </Show>
              </div>
              <div>
                <h3 class="text-xl font-bold text-gray-900 leading-tight">{props.title}</h3>
                <div class="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mt-1">Confirmation Required</div>
              </div>
            </div>

            <p class="text-gray-600 text-sm leading-relaxed mb-8">
              {props.message}
            </p>

            <div class="flex flex-col sm:flex-row-reverse gap-3">
              <button
                type="button"
                onClick={props.onConfirm}
                class={`w-full sm:flex-1 py-3 px-4 rounded-2xl text-white font-bold text-sm transition-all duration-300 active:scale-95 shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 ${typeClasses().button}`}
              >
                {props.confirmText || 'Confirm'}
              </button>
              <button
                type="button"
                onClick={props.onCancel}
                class="w-full sm:flex-1 py-3 px-4 rounded-2xl text-gray-600 font-bold text-sm bg-gray-50 hover:bg-gray-100 transition-all duration-300 active:scale-95 border border-gray-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-200"
              >
                {props.cancelText || 'Cancel'}
              </button>
            </div>
          </div>
          
          {/* Subtle bottom accent */}
          <div class={`h-1 w-full ${typeClasses().button.split(' ')[0]}`} />
        </div>
      </div>
    </Show>
  );
}
