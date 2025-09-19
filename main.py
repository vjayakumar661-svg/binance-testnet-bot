import MetaTrader5 as mt5

LOGIN = 213669683
PASSWORD = "j&LUr2Xu"   # email/dashboardல வந்த trader password paste பண்ணுங்க
SERVER = "OctaFX-Demo"

# Connect to MT5
if not mt5.initialize(login=LOGIN, password=PASSWORD, server=SERVER):
    print("❌ Connection failed")
    mt5.shutdown()
else:
    print("✅ Connected to MT5 successfully!")

    # Get account info
    account_info = mt5.account_info()
    if account_info != None:
        print(f"Balance: {account_info.balance}")
        print(f"Leverage: {account_info.leverage}")
        print(f"Currency: {account_info.currency}")
    else:
        print("Unable to retrieve account info")

    mt5.shutdown()
    
