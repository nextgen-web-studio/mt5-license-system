#property strict
#property version "1.00"

input string MT5_ID = "TEST001";
input string EXPIRY = "2026-1-2-31";
input string PLAN   = "premium";

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