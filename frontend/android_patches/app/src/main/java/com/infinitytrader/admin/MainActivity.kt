package com.infinitytrader.admin

import android.os.Bundle
import com.getcapacitor.BridgeActivity
import com.infinitytrader.admin.plugins.BackgroundPlugin

class MainActivity : BridgeActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        registerPlugin(BackgroundPlugin::class.java)
        super.onCreate(savedInstanceState)
    }
}
