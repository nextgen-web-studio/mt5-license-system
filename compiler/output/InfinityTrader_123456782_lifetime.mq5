#property strict
#property version "1.00"

input string MT5_ID = "123456782";
input string EXPIRY = "lifetime";
input string PLAN   = "Infinity Trader EA - Lifetime";

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