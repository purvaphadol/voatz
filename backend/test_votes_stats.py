#!/usr/bin/env python3
"""
Test script to debug votes stats endpoint
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, Vote

def test_vote_stats_logic():
    """Test the logic inside get_vote_stats function"""
    app = create_app()
    
    with app.app_context():
        print("🧪 Testing votes stats logic...")
        
        try:
            # Simulate the company_id (assuming company 1)
            company_id = 1
            print(f"✅ Using company_id: {company_id}")
            
            # Test each query individually
            print("\n📊 Testing individual queries:")
            
            total_votes = Vote.query.filter_by(company_id=company_id).count()
            print(f"  ✅ total_votes: {total_votes}")
            
            verified_votes = Vote.query.filter_by(company_id=company_id, vote_status='verified').count()
            print(f"  ✅ verified_votes: {verified_votes}")
            
            counted_votes = Vote.query.filter_by(company_id=company_id, is_counted=True).count()
            print(f"  ✅ counted_votes: {counted_votes}")
            
            flagged_votes = Vote.query.filter_by(company_id=company_id, vote_status='flagged').count()
            print(f"  ✅ flagged_votes: {flagged_votes}")
            
            # Test complex queries
            print("\n🔍 Testing complex queries:")
            
            try:
                vote_methods = db.session.query(
                    Vote.vote_method,
                    db.func.count(Vote.id).label('count')
                ).filter_by(company_id=company_id).group_by(Vote.vote_method).all()
                print(f"  ✅ vote_methods: {len(vote_methods)} groups")
            except Exception as e:
                print(f"  ❌ vote_methods error: {e}")
            
            try:
                vote_statuses = db.session.query(
                    Vote.vote_status,
                    db.func.count(Vote.id).label('count')
                ).filter_by(company_id=company_id).group_by(Vote.vote_status).all()
                print(f"  ✅ vote_statuses: {len(vote_statuses)} groups")
            except Exception as e:
                print(f"  ❌ vote_statuses error: {e}")
            
            # Test verification counts (using actual DB columns)
            try:
                biometric_verified_count = Vote.query.filter_by(company_id=company_id, biometric_verified=True).count()
                device_verified_count = Vote.query.filter_by(company_id=company_id, device_verified=True).count()
                identity_verified_count = Vote.query.filter_by(company_id=company_id, identity_verified=True).count()
                two_factor_verified_count = Vote.query.filter_by(company_id=company_id, two_factor_verified=True).count()
                print(f"  ✅ biometric_verified: {biometric_verified_count}")
                print(f"  ✅ device_verified: {device_verified_count}")
                print(f"  ✅ identity_verified: {identity_verified_count}")
                print(f"  ✅ two_factor_verified: {two_factor_verified_count}")
            except Exception as e:
                print(f"  ❌ verification counts error: {e}")
            
            # Test response construction
            print("\n📦 Testing response construction:")
            
            try:
                verification_rate = (verified_votes / total_votes * 100) if total_votes > 0 else 0
                print(f"  ✅ verification_rate: {verification_rate}%")
                
                response_data = {
                    'total_votes': total_votes,
                    'verified_votes': verified_votes,
                    'counted_votes': counted_votes,
                    'flagged_votes': flagged_votes,
                    'pending_votes': total_votes - verified_votes - flagged_votes,
                    'verification_rate': verification_rate,
                    'vote_methods': {method: count for method, count in vote_methods},
                    'vote_statuses': {status: count for status, count in vote_statuses},
                    'verification_types': {
                        'biometric_verified': biometric_verified_count,
                        'device_verified': device_verified_count,
                        'identity_verified': identity_verified_count,
                        'two_factor_verified': two_factor_verified_count
                    }
                }
                print(f"  ✅ Response data constructed successfully")
                print(f"  📄 Response: {response_data}")
                
            except Exception as e:
                print(f"  ❌ Response construction error: {e}")
                
        except Exception as e:
            print(f"❌ Overall error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_vote_stats_logic() 