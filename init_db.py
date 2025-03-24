from app import app, db, Bus

# Sample bus data with SCMS and Ernakulam locations
buses = [
    {
        'bus_number': 'KL-07-SC001',
        'source': 'SCMS School of Engineering and Technology',
        'destination': 'Edappally',
        'departure_time': '08:00 AM',
        'available_seats': 40,
        'price': 30.00
    },
    {
        'bus_number': 'KL-07-SC002',
        'source': 'SCMS School of Engineering and Technology',
        'destination': 'Aluva',
        'departure_time': '08:30 AM',
        'available_seats': 35,
        'price': 40.00
    },
    {
        'bus_number': 'KL-07-SC003',
        'source': 'SCMS School of Engineering and Technology',
        'destination': 'Kakkanad',
        'departure_time': '09:00 AM',
        'available_seats': 38,
        'price': 35.00
    },
    {
        'bus_number': 'KL-07-SC004',
        'source': 'Kaloor',
        'destination': 'SCMS School of Engineering and Technology',
        'departure_time': '07:30 AM',
        'available_seats': 42,
        'price': 35.00
    },
    {
        'bus_number': 'KL-07-SC005',
        'source': 'Vytilla',
        'destination': 'SCMS School of Engineering and Technology',
        'departure_time': '07:45 AM',
        'available_seats': 40,
        'price': 30.00
    },
    {
        'bus_number': 'KL-07-SC006',
        'source': 'SCMS School of Engineering and Technology',
        'destination': 'MG Road',
        'departure_time': '04:30 PM',
        'available_seats': 45,
        'price': 40.00
    },
    {
        'bus_number': 'KL-07-SC007',
        'source': 'SCMS School of Engineering and Technology',
        'destination': 'Fort Kochi',
        'departure_time': '04:45 PM',
        'available_seats': 38,
        'price': 50.00
    },
    {
        'bus_number': 'KL-07-SC008',
        'source': 'Palarivattom',
        'destination': 'SCMS School of Engineering and Technology',
        'departure_time': '08:15 AM',
        'available_seats': 40,
        'price': 35.00
    },
    {
        'bus_number': 'KL-07-SC009',
        'source': 'SCMS School of Engineering and Technology',
        'destination': 'Lulu Mall',
        'departure_time': '05:00 PM',
        'available_seats': 42,
        'price': 35.00
    },
    {
        'bus_number': 'KL-07-SC010',
        'source': 'Marine Drive',
        'destination': 'SCMS School of Engineering and Technology',
        'departure_time': '07:15 AM',
        'available_seats': 40,
        'price': 45.00
    }
]

def init_db():
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Delete existing bus data
        Bus.query.delete()
        
        # Add new sample buses
        for bus_data in buses:
            bus = Bus(**bus_data)
            db.session.add(bus)
        
        # Commit the changes
        db.session.commit()
        print("Sample bus data added successfully!")

if __name__ == '__main__':
    init_db() 