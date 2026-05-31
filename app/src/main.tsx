import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import { LanguageProvider } from './shared/i18n';
import { ModelStatusProvider } from './shared/modelStatus';
import { ThemeProvider } from './shared/theme';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ThemeProvider>
      <LanguageProvider>
        <ModelStatusProvider>
          <App />
        </ModelStatusProvider>
      </LanguageProvider>
    </ThemeProvider>
  </React.StrictMode>,
);
