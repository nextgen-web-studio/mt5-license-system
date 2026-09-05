package com.infinitytrader.admin.services

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import com.infinitytrader.admin.networking.ApiClient

class AdminBackgroundService : Service() {
    private val scope = CoroutineScope(Dispatchers.IO + Job())
    private val CHANNEL_ID = "AdminBackgroundChannel"
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(1, createNotification("Monitoring Admin Systems..."))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        scope.launch {
            while (isActive) {
                // Background processing: Safely call FastAPI to check for critical alerts
                try {
                    val alerts = ApiClient.checkCriticalAlerts()
                    if (alerts.isNotEmpty()) {
                        showAlertNotification(alerts)
                    }
                } catch (e: Exception) {
                    // Handle network failure gracefully without crashing
                }
                delay(60000) // 1 minute interval, respects battery
            }
        }
        // STICKY allows safe recovery if Android kills the service for memory
        return START_STICKY 
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Admin Background Service",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(text: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Infinity Trader")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .build()
    }

    private fun showAlertNotification(alert: String) {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Admin Alert")
            .setContentText(alert)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
        manager.notify(System.currentTimeMillis().toInt(), notification)
    }
}
