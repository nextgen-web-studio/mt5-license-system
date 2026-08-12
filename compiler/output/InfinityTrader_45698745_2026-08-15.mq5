#property strict
#property version "1.00"

input string MT5_ID = "45698745";
input string EXPIRY = "2026-08-15";
input string PLAN   = "standard";

int OnInit()
{
   Print("Infinity Trader EA initialized");
   Print("MT5 ID: ", MT5_ID);
   Print("Expiry: ", EXPIRY);
   Print("Plan: ", PLAN);

   return(INIT_SUCCEEDED);
}

void OnTick()
{
}