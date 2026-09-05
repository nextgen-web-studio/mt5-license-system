import { registerPlugin } from '@capacitor/core';

export interface AdminNativePlugin {
  startBackgroundService(): Promise<void>;
  stopBackgroundService(): Promise<void>;
  saveSecureToken(options: { token: string }): Promise<void>;
}

const AdminNative = registerPlugin<AdminNativePlugin>('AdminNative');

export default AdminNative;
