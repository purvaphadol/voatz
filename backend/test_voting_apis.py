#!/usr/bin/env python3
"""
Comprehensive test script for Voatz voting system APIs
Tests all CRUD operations for the voting system endpoints
"""

import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:4000/api"

class VotingAPITester:
    def __init__(self):
        self.token = None
        self.company_id = None
        self.created_ids = {
            'voters': [],
            'elections': [],
            'ballots': [],
            'candidates': [],
            'votes': [],
            'registrations': []
        }

    def login(self):
        """Login to get authentication token"""
        login_data = {
            "email": "rushiraj@datagrid.co.in",
            "password": "admin123"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
            self.company_id = data['user']['company_id']
            print(f"✅ Login successful. Company ID: {self.company_id}")
            return True
        else:
            print(f"❌ Login failed: {response.text}")
            return False

    def get_headers(self):
        """Get request headers with authentication"""
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def test_voters_api(self):
        """Test voters API endpoints"""
        print("\n🗳️  Testing Voters API...")
        
        # Test GET /api/voters
        response = requests.get(f"{BASE_URL}/voters", headers=self.get_headers())
        print(f"GET /voters: {response.status_code}")
        
        # Test POST /api/voters (create new user + voter)
        voter_data = {
            "name": "John Doe",
            "email": f"john.doe.{int(time.time())}@example.com",
            "password": "password123",
            "phone_number": "+1234567890",
            "date_of_birth": "1990-01-01",
            "registered_address": "123 Main St, City, State",
            "jurisdiction": "District 1"
        }
        
        response = requests.post(f"{BASE_URL}/voters", json=voter_data, headers=self.get_headers())
        if response.status_code == 201:
            voter_id = response.json()['voter_id']
            self.created_ids['voters'].append(voter_id)
            print(f"✅ Created voter ID: {voter_id}")
            
            # Test GET /api/voters/{id}
            response = requests.get(f"{BASE_URL}/voters/{voter_id}", headers=self.get_headers())
            print(f"GET /voters/{voter_id}: {response.status_code}")
            
            # Test PUT /api/voters/{id}
            update_data = {"phone_number": "+0987654321"}
            response = requests.put(f"{BASE_URL}/voters/{voter_id}", json=update_data, headers=self.get_headers())
            print(f"PUT /voters/{voter_id}: {response.status_code}")
            
        else:
            print(f"❌ Failed to create voter: {response.text}")

    def test_elections_api(self):
        """Test elections API endpoints"""
        print("\n🏛️  Testing Elections API...")
        
        # Test GET /api/elections
        response = requests.get(f"{BASE_URL}/elections", headers=self.get_headers())
        print(f"GET /elections: {response.status_code}")
        
        # Test POST /api/elections
        start_date = (datetime.now() + timedelta(days=1)).isoformat()
        end_date = (datetime.now() + timedelta(days=30)).isoformat()
        
        election_data = {
            "title": f"Test Election {int(time.time())}",
            "description": "Test election for API validation",
            "election_type": "municipal",
            "start_date": start_date,
            "end_date": end_date,
            "require_biometric": True,
            "require_photo_id": True
        }
        
        response = requests.post(f"{BASE_URL}/elections", json=election_data, headers=self.get_headers())
        if response.status_code == 201:
            election_id = response.json()['election_id']
            self.created_ids['elections'].append(election_id)
            print(f"✅ Created election ID: {election_id}")
            
            # Test GET /api/elections/{id}
            response = requests.get(f"{BASE_URL}/elections/{election_id}", headers=self.get_headers())
            print(f"GET /elections/{election_id}: {response.status_code}")
            
            # Test PUT /api/elections/{id}
            update_data = {"description": "Updated test election description"}
            response = requests.put(f"{BASE_URL}/elections/{election_id}", json=update_data, headers=self.get_headers())
            print(f"PUT /elections/{election_id}: {response.status_code}")
            
            return election_id
        else:
            print(f"❌ Failed to create election: {response.text}")
            return None

    def test_ballots_api(self, election_id):
        """Test ballots API endpoints"""
        print("\n🗳️  Testing Ballots API...")
        
        if not election_id:
            print("❌ No election ID available for ballot testing")
            return None
        
        # Test GET /api/ballots
        response = requests.get(f"{BASE_URL}/ballots", headers=self.get_headers())
        print(f"GET /ballots: {response.status_code}")
        
        # Test POST /api/ballots
        ballot_data = {
            "title": f"Test Ballot {int(time.time())}",
            "description": "Test ballot for mayor position",
            "election_id": election_id,
            "ballot_type": "single_choice",
            "position_title": "Mayor",
            "max_selections": 1,
            "require_selection": True
        }
        
        response = requests.post(f"{BASE_URL}/ballots", json=ballot_data, headers=self.get_headers())
        if response.status_code == 201:
            ballot_id = response.json()['ballot_id']
            self.created_ids['ballots'].append(ballot_id)
            print(f"✅ Created ballot ID: {ballot_id}")
            
            # Test GET /api/ballots/{id}
            response = requests.get(f"{BASE_URL}/ballots/{ballot_id}", headers=self.get_headers())
            print(f"GET /ballots/{ballot_id}: {response.status_code}")
            
            return ballot_id
        else:
            print(f"❌ Failed to create ballot: {response.text}")
            return None

    def test_candidates_api(self, ballot_id):
        """Test candidates API endpoints"""
        print("\n👤 Testing Candidates API...")
        
        if not ballot_id:
            print("❌ No ballot ID available for candidate testing")
            return None
        
        # Test GET /api/candidates
        response = requests.get(f"{BASE_URL}/candidates", headers=self.get_headers())
        print(f"GET /candidates: {response.status_code}")
        
        # Test POST /api/candidates (create multiple candidates)
        candidates_data = [
            {
                "name": "Alice Johnson",
                "ballot_id": ballot_id,
                "party": "Democratic Party",
                "party_abbreviation": "DEM",
                "title": "Current City Councilwoman",
                "is_incumbent": True
            },
            {
                "name": "Bob Smith",
                "ballot_id": ballot_id,
                "party": "Republican Party",
                "party_abbreviation": "REP",
                "title": "Business Owner"
            }
        ]
        
        candidate_ids = []
        for candidate_data in candidates_data:
            response = requests.post(f"{BASE_URL}/candidates", json=candidate_data, headers=self.get_headers())
            if response.status_code == 201:
                candidate_id = response.json()['candidate_id']
                candidate_ids.append(candidate_id)
                self.created_ids['candidates'].append(candidate_id)
                print(f"✅ Created candidate ID: {candidate_id}")
            else:
                print(f"❌ Failed to create candidate: {response.text}")
        
        if candidate_ids:
            # Test GET /api/candidates/{id}
            response = requests.get(f"{BASE_URL}/candidates/{candidate_ids[0]}", headers=self.get_headers())
            print(f"GET /candidates/{candidate_ids[0]}: {response.status_code}")
            
            return candidate_ids
        
        return None

    def test_voter_registrations_api(self, voter_id, election_id):
        """Test voter registrations API endpoints"""
        print("\n📝 Testing Voter Registrations API...")
        
        if not voter_id or not election_id:
            print("❌ No voter ID or election ID available for registration testing")
            return None
        
        # Test GET /api/voter-registrations
        response = requests.get(f"{BASE_URL}/voter-registrations", headers=self.get_headers())
        print(f"GET /voter-registrations: {response.status_code}")
        
        # Test POST /api/voter-registrations
        registration_data = {
            "voter_id": voter_id,
            "election_id": election_id,
            "registration_type": "standard",
            "preferred_language": "en"
        }
        
        response = requests.post(f"{BASE_URL}/voter-registrations", json=registration_data, headers=self.get_headers())
        if response.status_code == 201:
            registration_id = response.json()['id']
            self.created_ids['registrations'].append(registration_id)
            print(f"✅ Created registration ID: {registration_id}")
            
            # Test approve registration
            approval_data = {"notes": "Approved for testing"}
            response = requests.post(f"{BASE_URL}/voter-registrations/{registration_id}/approve", 
                                   json=approval_data, headers=self.get_headers())
            print(f"POST /voter-registrations/{registration_id}/approve: {response.status_code}")
            
            return registration_id
        else:
            print(f"❌ Failed to create voter registration: {response.text}")
            return None

    def test_votes_api(self, voter_id, ballot_id, candidate_ids):
        """Test votes API endpoints"""
        print("\n🗳️  Testing Votes API...")
        
        if not voter_id or not ballot_id or not candidate_ids:
            print("❌ Missing required IDs for vote testing")
            return
        
        # Test GET /api/votes
        response = requests.get(f"{BASE_URL}/votes", headers=self.get_headers())
        print(f"GET /votes: {response.status_code}")
        
        # Test POST /api/votes (cast a vote)
        vote_data = {
            "voter_id": voter_id,
            "ballot_id": ballot_id,
            "vote_data": {
                "selections": [candidate_ids[0]],  # Vote for first candidate
                "ballot_type": "single_choice"
            },
            "vote_method": "admin",
            "biometric_verified": True,
            "device_verified": True,
            "identity_verified": True
        }
        
        response = requests.post(f"{BASE_URL}/votes", json=vote_data, headers=self.get_headers())
        if response.status_code == 201:
            vote_id = response.json()['vote_id']
            print(f"✅ Cast vote ID: {vote_id}")
            
            # Test vote tracking
            tracking_code = response.json()['tracking_code']
            response = requests.get(f"{BASE_URL}/votes/tracking/{tracking_code}")
            print(f"GET /votes/tracking/{tracking_code}: {response.status_code}")
            
        else:
            print(f"❌ Failed to cast vote: {response.text}")

    def test_stats_endpoints(self):
        """Test statistics endpoints"""
        print("\n📊 Testing Statistics Endpoints...")
        
        endpoints = [
            "/voters/stats",
            "/elections/stats",
            "/ballots/stats",
            "/candidates/stats",
            "/votes/stats",
            "/voter-registrations/stats"
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=self.get_headers())
            print(f"GET {endpoint}: {response.status_code}")

    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting comprehensive Voatz API testing...\n")
        
        # Login first
        if not self.login():
            return
        
        # Run tests in logical order
        self.test_voters_api()
        
        # Get voter ID for later tests
        voter_id = self.created_ids['voters'][0] if self.created_ids['voters'] else None
        
        # Test elections
        election_id = self.test_elections_api()
        
        # Test ballots
        ballot_id = self.test_ballots_api(election_id)
        
        # Test candidates
        candidate_ids = self.test_candidates_api(ballot_id)
        
        # Test voter registrations
        registration_id = self.test_voter_registrations_api(voter_id, election_id)
        
        # Test votes
        self.test_votes_api(voter_id, ballot_id, candidate_ids)
        
        # Test stats endpoints
        self.test_stats_endpoints()
        
        print("\n✅ Comprehensive API testing completed!")
        print(f"\nCreated resources for cleanup:")
        for resource_type, ids in self.created_ids.items():
            if ids:
                print(f"  {resource_type}: {ids}")

if __name__ == "__main__":
    tester = VotingAPITester()
    tester.run_comprehensive_test() 