package com.infinitytrader.admin.networking

import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

object ApiClient {
    // Isolated native networking layer just for background service
    // Uses the existing FastAPI endpoint safely
    suspend fun checkCriticalAlerts(): String = withContext(Dispatchers.IO) {
        try {
            val url = URL("https://api.infinitytrader.com/api/v1/admin/alerts")
            val connection = url.openConnection() as HttpURLConnection
            connection.requestMethod = "GET"
            connection.connectTimeout = 10000
            connection.readTimeout = 10000
            
            if (connection.responseCode == 200) {
                return@withContext connection.inputStream.bufferedReader().use { it.readText() }
            }
        } catch (e: Exception) {
            // Log error internally, do not crash service
        }
        return@withContext ""
    }
}
