/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_COGNITO_DOMAIN: string
    readonly VITE_COGNITO_APP_CLIENT_ID: string
    readonly VITE_REDIRECT_URI: string
    readonly GEMINI_API_KEY: string
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}
