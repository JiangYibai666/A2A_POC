#!/usr/bin/env python3
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_chat_api():
    """Test the chat API endpoint"""
    print("=" * 60)
    print("Testing A2A POC Frontend Integration")
    print("=" * 60)
    
    # Test request
    test_input = "帮我预订机票和酒店，5月1日从新加坡飞上海，5月4日返回"
    print(f"\n📝 Test Input: {test_input}")
    print("-" * 60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"user_input": test_input},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        combined_options = data.get('combined_options', [])
        
        print(f"\n✅ API Response Status: {response.status_code}")
        print(f"📊 Found {len(combined_options)} combined options")
        
        if combined_options:
            option = combined_options[0]
            print("\n🎫 First Option Details:")
            print(f"  Outbound Flight:")
            print(f"    - Flight Number: {option['outbound'].get('flight_number')}")
            print(f"    - Airline: {option['outbound'].get('airline')}")
            print(f"    - Departure: {option['outbound'].get('departure_time')}")
            print(f"    - Arrival: {option['outbound'].get('arrival_time')}")
            print(f"    - Duration: {option['outbound'].get('duration')}")
            print(f"    - Price: ${option['outbound'].get('price')}")
            
            print(f"\n  Return Flight:")
            print(f"    - Flight Number: {option['return'].get('flight_number')}")
            print(f"    - Airline: {option['return'].get('airline')}")
            print(f"    - Departure: {option['return'].get('departure_time')}")
            print(f"    - Arrival: {option['return'].get('arrival_time')}")
            print(f"    - Duration: {option['return'].get('duration')}")
            print(f"    - Price: ${option['return'].get('price')}")
            
            print(f"\n  Hotel:")
            print(f"    - Name: {option['hotel'].get('name')}")
            print(f"    - Area: {option['hotel'].get('area')}")
            print(f"    - Stars: {option['hotel'].get('stars')}")
            print(f"    - Checkin: {option['hotel'].get('checkin_time')}")
            print(f"    - Checkout: {option['hotel'].get('checkout_time')}")
            print(f"    - Price: {option['hotel'].get('price')}")
            
            # Verify all required fields
            print("\n📋 Field Validation:")
            outbound_fields = ['flight_number', 'airline', 'departure_time', 'arrival_time', 'duration', 'price']
            return_fields = ['flight_number', 'airline', 'departure_time', 'arrival_time', 'duration', 'price']
            hotel_fields = ['name', 'area', 'stars', 'checkin_time', 'checkout_time', 'price']
            
            all_valid = True
            for field in outbound_fields:
                exists = field in option['outbound']
                print(f"  ✓ Outbound.{field}: {'✅' if exists else '❌'}")
                all_valid = all_valid and exists
                
            for field in return_fields:
                exists = field in option['return']
                print(f"  ✓ Return.{field}: {'✅' if exists else '❌'}")
                all_valid = all_valid and exists
                
            for field in hotel_fields:
                exists = field in option['hotel']
                print(f"  ✓ Hotel.{field}: {'✅' if exists else '❌'}")
                all_valid = all_valid and exists
            
            if all_valid:
                print("\n🎉 All required fields are present!")
                print("\n✨ Frontend should work correctly now!")
                print("\n🌐 Open http://localhost:3000/poc.html in your browser")
            else:
                print("\n⚠️  Some fields are missing!")
                
        else:
            print("\n❌ No combined options returned!")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ API Error: {e}")
        print("\nMake sure:")
        print("  1. Backend API is running on http://localhost:8000")
        print("  2. Database is initialized")
        print("  3. Agents are properly registered")

if __name__ == "__main__":
    print("\n⏳ Waiting for API to be ready...")
    time.sleep(2)
    test_chat_api()
