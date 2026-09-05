package com.infinitytrader.admin.plugins

import android.content.Intent
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.infinitytrader.admin.services.AdminBackgroundService
import com.infinitytrader.admin.storage.SecureStorage

@CapacitorPlugin(name = "AdminNative")
class BackgroundPlugin : Plugin() {

    @PluginMethod
    fun startBackgroundService(call: PluginCall) {
        val context = context
        val serviceIntent = Intent(context, AdminBackgroundService::class.java)
        context.startForegroundService(serviceIntent)
        call.resolve()
    }

    @PluginMethod
    fun stopBackgroundService(call: PluginCall) {
        val context = context
        val serviceIntent = Intent(context, AdminBackgroundService::class.java)
        context.stopService(serviceIntent)
        call.resolve()
    }

    @PluginMethod
    fun saveSecureToken(call: PluginCall) {
        val token = call.getString("token")
        if (token != null) {
            SecureStorage.saveToken(context, token)
            call.resolve()
        } else {
            call.reject("Token is required")
        }
    }
}
