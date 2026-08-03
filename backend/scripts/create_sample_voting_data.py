#!/usr/bin/env python3
"""
Simple Voting Data Script
Creates basic sample data for the voting system
"""

from app import create_app
from app.models.user import User
from app.models.company import Company
from app.models.voter import Voter
from app.models.election import Election
from app.models.ballot import Ballot
from app.models.candidate import Candidate
from app.models.vote import Vote
from app.models.voter_registration import VoterRegistration
from app import db
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import random

def create_simple_voting_data():
    """Create simple voting sample data"""
    app = create_app()
    
    with app.app_context():
        print("🗑️  Deleting existing voting records...")
        
        # Delete in order to maintain referential integrity
        Vote.query.delete()
        VoterRegistration.query.delete()
        Candidate.query.delete()
        Ballot.query.delete()
        Election.query.delete()
        Voter.query.delete()
        
        db.session.commit()
        print("✅ All voting records deleted")
        
        # Get company for sample data
        company = Company.query.first()
        if not company:
            print("❌ No company found")
            return
            
        print(f"📊 Adding sample data for company: {company.company_name}")
        
        # Create 5 sample users for voters
        print("👥 Creating sample users...")
        users = []
        for i in range(5):
            email = f"voter{i+1}@example.com"
            existing_user = User.query.filter_by(email=email).first()
            
            if not existing_user:
                user = User()
                user.name = f"Voter {i+1}"
                user.email = email
                user.password_hash = generate_password_hash("voter123")
                user.company_id = company.id
                user.status = 1
                db.session.add(user)
                users.append(user)
            else:
                users.append(existing_user)
        
        db.session.commit()
        print(f"✅ Created {len(users)} users")
        
        # Create voters
        print("🗳️  Creating voters...")
        voters = []
        for i, user in enumerate(users):
            voter = Voter()
            voter.user_id = user.id
            voter.company_id = company.id
            voter.voter_id = f"VOTER{str(i+1).zfill(3)}"
            voter.phone_number = f"+1-555-010{i+1}"
            voter.date_of_birth = datetime(1990 + i, 1, 15).date()
            voter.is_verified = True
            voter.verification_level = "standard"
            voter.voter_type = "standard"
            voter.two_factor_enabled = False
            voter.status = 1
            db.session.add(voter)
            voters.append(voter)
        
        db.session.commit()
        print(f"✅ Created {len(voters)} voters")
        
        # Create a simple election
        print("🏛️  Creating election...")
        election = Election()
        election.company_id = company.id
        election.title = "2024 Sample Election"
        election.description = "Sample election for testing"
        election.election_code = "SAMPLE2024"
        election.election_type = "general"
        election.start_date = datetime.utcnow() + timedelta(days=1)
        election.end_date = datetime.utcnow() + timedelta(days=8)
        election.registration_deadline = datetime.utcnow() + timedelta(hours=12)
        election.status = 1
        election.max_votes_per_voter = 1
        election.require_photo_id = True
        election.require_biometric = False
        election.audit_enabled = True
        election.paper_trail_required = True
        db.session.add(election)
        db.session.commit()
        print("✅ Created election")
        
        # Create a simple ballot
        print("📋 Creating ballot...")
        ballot = Ballot()
        ballot.company_id = company.id
        ballot.election_id = election.id
        ballot.title = "Mayor Election"
        ballot.description = "Vote for Mayor"
        ballot.ballot_code = "MAYOR2024"
        ballot.ballot_type = "single_choice"
        ballot.min_selections = 1
        ballot.max_selections = 1
        ballot.is_active = True
        ballot.is_published = True
        ballot.order_index = 1
        ballot.instructions = "Select one candidate for Mayor"
        ballot.status = 1
        db.session.add(ballot)
        db.session.commit()
        print("✅ Created ballot")
        
        # Create simple candidates
        print("🏃 Creating candidates...")
        candidates_data = [
            {"name": "John Smith", "party": "Independent"},
            {"name": "Jane Doe", "party": "Progressive"},
            {"name": "Bob Johnson", "party": "Conservative"}
        ]
        
        candidates = []
        for i, cand_data in enumerate(candidates_data):
            candidate = Candidate()
            candidate.company_id = company.id
            candidate.ballot_id = ballot.id
            candidate.name = cand_data["name"]
            candidate.candidate_code = f"CAND{i+1}"
            candidate.party = cand_data["party"]
            candidate.biography = f"Candidate {cand_data['name']} - {cand_data['party']}"
            candidate.order_index = i + 1
            candidate.is_active = True
            candidate.is_qualified = True
            candidate.status = 1
            db.session.add(candidate)
            candidates.append(candidate)
        
        db.session.commit()
        print(f"✅ Created {len(candidates)} candidates")
        
        # Create voter registrations
        print("📝 Creating voter registrations...")
        registrations = []
        for voter in voters:
            registration = VoterRegistration()
            registration.company_id = company.id
            registration.voter_id = voter.id
            registration.election_id = election.id
            registration.registration_id = f"REG{voter.id}{election.id}"
            registration.registration_type = "standard"
            registration.registered_at = datetime.utcnow() - timedelta(days=1)
            registration.status = "approved"
            registration.approved_at = datetime.utcnow() - timedelta(hours=12)
            registration.eligibility_verified = True
            registration.identity_verified = True
            registration.address_verified = True
            registration.age_verified = True
            registration.required_verification_level = "standard"
            registration.verification_level_met = "standard"
            registration.registered_address = f"123 Main St, City"
            registration.jurisdiction = "District-1"
            registration.preferred_language = "en"
            registration.registration_source = "admin_portal"
            registration.registration_method = "online"
            db.session.add(registration)
            registrations.append(registration)
        
        db.session.commit()
        print(f"✅ Created {len(registrations)} voter registrations")
        
        # Create some sample votes
        print("🗳️  Creating sample votes...")
        votes = []
        for i, registration in enumerate(registrations[:3]):  # Only first 3 voters vote
            selected_candidate = candidates[i % len(candidates)]
            
            vote = Vote()
            vote.company_id = company.id
            vote.voter_id = registration.voter_id
            vote.election_id = election.id
            vote.ballot_id = ballot.id
            vote.vote_id = f"VOTE{registration.voter_id}{election.id}"
            vote.tracking_code = f"TRACK{random.randint(100000, 999999)}"
            vote.vote_cast_time = datetime.utcnow() - timedelta(hours=random.randint(1, 12))
            vote.vote_method = "online"
            vote.vote_status = "verified"
            vote.signature_hash = f"sig_{random.randint(1000, 9999)}"
            vote.ip_address = f"192.168.1.{random.randint(1, 255)}"
            vote.audit_trail = [{"event": "vote_cast", "timestamp": vote.vote_cast_time.isoformat()}]
            vote.status = 1
            
            # Add required vote data and hashes
            vote.vote_data = {"selections": [selected_candidate.id], "rankings": [], "write_ins": []}
            vote.vote_hash = f"hash_{random.randint(10000, 99999)}"
            vote.verification_hash = f"verify_{random.randint(10000, 99999)}"
            
            db.session.add(vote)
            votes.append(vote)
        
        db.session.commit()
        print(f"✅ Created {len(votes)} sample votes")
        
        # Update election statistics
        election.total_registered_voters = len(registrations)
        election.total_votes_cast = len(votes)
        db.session.commit()
        
        print("\n🎉 Simple voting data created successfully!")
        print(f"   👥 Users: {len(users)}")
        print(f"   🗳️  Voters: {len(voters)}")
        print(f"   🏛️  Elections: 1")
        print(f"   📋 Ballots: 1")
        print(f"   🏃 Candidates: {len(candidates)}")
        print(f"   📝 Registrations: {len(registrations)}")
        print(f"   ✅ Votes: {len(votes)}")
        
        return True

if __name__ == "__main__":
    create_simple_voting_data() 