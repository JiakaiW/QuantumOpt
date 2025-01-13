import React from 'react'
import ReactDOM from 'react-dom/client'
import { ThemeProvider, createTheme } from '@mui/material'
import { OptimizationProvider } from './contexts/OptimizationContext'
import App from './App'
import './index.css'

const theme = createTheme({
  typography: {
    fontFamily: '-apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },
  components: {
    MuiPaper: {
      defaultProps: {
        elevation: 0
      },
      styleOverrides: {
        root: {
          backgroundColor: '#fff'
        }
      }
    }
  }
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <OptimizationProvider>
        <App />
      </OptimizationProvider>
    </ThemeProvider>
  </React.StrictMode>
) 