@echo off
echo Installing Capacitor...
call npm install @capacitor/core @capacitor/android
call npm install -D @capacitor/cli

echo Initializing Capacitor...
call npx cap init "Infinity Trader Admin" "com.infinitytrader.admin" --web-dir out

echo Adding Android Platform...
call npx cap add android

echo Applying Native Kotlin Patches...
xcopy /E /Y android_patches\* android\

echo Syncing...
call npx cap sync android

echo Setup Complete! You can now open frontend/android in Android Studio.
