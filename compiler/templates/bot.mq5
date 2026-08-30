#property strict
#property version "1.00"

int ALLOWED_MT5_ID = 123456789;
datetime LICENSE_EXPIRY = D'2099.01.01';

int OnInit()
{
   Print("Infinity Trader EA initialized");
   
   if(AccountInfoInteger(ACCOUNT_LOGIN) != ALLOWED_MT5_ID) {
      Print("Invalid MT5 ID. License violation.");
      return INIT_FAILED;
   }
   
   if(TimeCurrent() > LICENSE_EXPIRY) {
      Print("License expired.");
      return INIT_FAILED;
   }
   
   return(INIT_SUCCEEDED);
}

void OnTick()
{
   // EA Logic goes here
}
