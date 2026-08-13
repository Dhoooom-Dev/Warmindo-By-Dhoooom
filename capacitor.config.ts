import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.dhoo_co.warmindo',
  appName: 'Warmindo By dhoo_co',
  webDir: 'android-web',
  bundledWebRuntime: false,
  server: { androidScheme: 'https' }
};

export default config;
