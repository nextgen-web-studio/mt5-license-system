import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.infinitytrader.admin',
  appName: 'Infinity Trader Admin',
  webDir: 'out',
  server: {
    // Option B: Point to the deployed Next.js application
    // This preserves server-side redirects, headers, and Next.js backend functionality.
    url: 'https://mt5-license-system.vercel.app',
    allowNavigation: [
      'mt5-license-system.vercel.app',
      'api.infinitytrader.com' // Example backend domain
    ],
    cleartext: true
  },
  android: {
    backgroundColor: "#0a0a0a",
    buildOptions: {
      keystorePath: 'release.keystore',
      keystoreAlias: 'upload',
    }
  },
  plugins: {
    PushNotifications: {
      presentationOptions: ["badge", "sound", "alert"]
    }
  }
};

export default config;
