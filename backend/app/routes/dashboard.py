from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.election import Election
from app.models.vote import Vote
from app.models.ballot import Ballot
from app.models.voter_registration import VoterRegistration
from app.utils import get_current_company_id, require_permission
from datetime import datetime, timedelta, timezone
from sqlalchemy import and_, or_

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/', methods=['GET'])
@require_permission('Dashboard', 'view')
def get_dashboard():
    """Get general dashboard data for mobile app"""
    try:
        company_id = get_current_company_id()
        now = datetime.now(timezone.utc)
        
        # Get active elections
        active_elections = Election.query.filter(
            Election.company_id == company_id,
            Election.start_date <= now,
            Election.end_date >= now,
            Election.status == 'active'
        ).all()
        
        # Get upcoming elections
        upcoming_elections = Election.query.filter(
            Election.company_id == company_id,
            Election.start_date > now,
            Election.status.in_(['draft', 'scheduled'])
        ).order_by(Election.start_date.asc()).limit(5).all()
        
        # Get recent completed elections
        completed_elections = Election.query.filter(
            Election.company_id == company_id,
            Election.status == 'completed'
        ).order_by(Election.end_date.desc()).limit(3).all()
        
        # Basic stats
        total_elections = Election.query.filter_by(company_id=company_id).count()
        total_votes = Vote.query.filter_by(company_id=company_id).count()
        
        return jsonify({
            'active_elections': [{
                'id': e.id,
                'title': e.title,
                'description': e.description,
                'election_type': e.election_type,
                'start_date': e.start_date.isoformat(),
                'end_date': e.end_date.isoformat(),
                'status': e.status,
                'total_votes_cast': e.total_votes_cast,
                'total_registered_voters': e.total_registered_voters
            } for e in active_elections],
            'upcoming_elections': [{
                'id': e.id,
                'title': e.title,
                'description': e.description,
                'election_type': e.election_type,
                'start_date': e.start_date.isoformat(),
                'end_date': e.end_date.isoformat(),
                'status': e.status
            } for e in upcoming_elections],
            'recent_completed': [{
                'id': e.id,
                'title': e.title,
                'election_type': e.election_type,
                'end_date': e.end_date.isoformat(),
                'status': e.status,
                'total_votes_cast': e.total_votes_cast,
                'results_published': e.results_published
            } for e in completed_elections],
            'stats': {
                'total_elections': total_elections,
                'active_elections': len(active_elections),
                'upcoming_elections': len(upcoming_elections),
                'total_votes': total_votes
            }
        })
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error in get_dashboard: {str(e)}")
        return jsonify({
            'active_elections': [],
            'upcoming_elections': [],
            'recent_completed': [],
            'stats': {
                'total_elections': 0,
                'active_elections': 0,
                'upcoming_elections': 0,
                'total_votes': 0
            }
        })

@dashboard_bp.route('/stats', methods=['GET'])
@require_permission('Dashboard', 'view')
def get_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    try:
        company_id = get_current_company_id()
        now = datetime.now(timezone.utc)
        
        # Election statistics
        total_elections = Election.query.filter_by(company_id=company_id).count()
        
        # Active elections (currently running)
        active_elections = Election.query.filter(
            Election.company_id == company_id,
            Election.start_date <= now,
            Election.end_date >= now,
            Election.status == 'active'
        ).count()
        
        # Upcoming elections (scheduled to start)
        upcoming_elections = Election.query.filter(
            Election.company_id == company_id,
            Election.start_date > now,
            Election.status.in_(['draft', 'scheduled'])
        ).count()
        
        # Completed elections
        completed_elections = Election.query.filter(
            Election.company_id == company_id,
            Election.status == 'completed'
        ).count()
        
        # Vote statistics
        total_votes = Vote.query.filter_by(company_id=company_id).count()
        verified_votes = Vote.query.filter_by(company_id=company_id, vote_status='verified').count()
        counted_votes = Vote.query.filter_by(company_id=company_id, is_counted=True).count()
        pending_votes = Vote.query.filter_by(company_id=company_id, vote_status='pending').count()
        
        # Recent activity (last 7 days)
        week_ago = now - timedelta(days=7)
        recent_votes = Vote.query.filter(
            Vote.company_id == company_id,
            Vote.vote_cast_time >= week_ago
        ).count()
        
        # Ballot statistics
        total_ballots = Ballot.query.join(Election).filter(
            Election.company_id == company_id
        ).count()
        
        active_ballots = Ballot.query.join(Election).filter(
            Election.company_id == company_id,
            Election.start_date <= now,
            Election.end_date >= now,
            Election.status == 'active'
        ).count()
        
        # Voter registration statistics
        total_registrations = VoterRegistration.query.join(Election).filter(
            Election.company_id == company_id
        ).count()
        
        approved_registrations = VoterRegistration.query.join(Election).filter(
            Election.company_id == company_id,
            VoterRegistration.status == 'approved'
        ).count()
        
        # Participation rate
        participation_rate = 0
        if approved_registrations > 0:
            participation_rate = (total_votes / approved_registrations) * 100
        
        # Verification rate
        verification_rate = 0
        if total_votes > 0:
            verification_rate = (verified_votes / total_votes) * 100
        
        return jsonify({
            'elections': {
                'total': total_elections,
                'active': active_elections,
                'upcoming': upcoming_elections,
                'completed': completed_elections
            },
            'votes': {
                'total': total_votes,
                'verified': verified_votes,
                'counted': counted_votes,
                'pending': pending_votes,
                'recent_week': recent_votes
            },
            'ballots': {
                'total': total_ballots,
                'active': active_ballots
            },
            'registrations': {
                'total': total_registrations,
                'approved': approved_registrations
            },
            'metrics': {
                'participation_rate': round(participation_rate, 2),
                'verification_rate': round(verification_rate, 2),
                'voter_turnout': round((total_votes / max(approved_registrations, 1)) * 100, 2)
            },
            'summary': {
                'elections_this_month': Election.query.filter(
                    Election.company_id == company_id,
                    Election.created_at >= now.replace(day=1)
                ).count(),
                'votes_today': Vote.query.filter(
                    Vote.company_id == company_id,
                    Vote.vote_cast_time >= now.replace(hour=0, minute=0, second=0)
                ).count(),
                'active_voting_sessions': active_elections
            }
        })
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error in get_dashboard_stats: {str(e)}")
        return jsonify({
            'elections': {'total': 0, 'active': 0, 'upcoming': 0, 'completed': 0},
            'votes': {'total': 0, 'verified': 0, 'counted': 0, 'pending': 0, 'recent_week': 0},
            'ballots': {'total': 0, 'active': 0},
            'registrations': {'total': 0, 'approved': 0},
            'metrics': {'participation_rate': 0, 'verification_rate': 0, 'voter_turnout': 0},
            'summary': {'elections_this_month': 0, 'votes_today': 0, 'active_voting_sessions': 0}
        })

@dashboard_bp.route('/recent-activity', methods=['GET'])
@require_permission('Dashboard', 'view')
def get_recent_activity():
    """Get recent voting activity for dashboard"""
    try:
        company_id = get_current_company_id()
        
        # Get recent votes (last 10)
        recent_votes = Vote.query.filter_by(company_id=company_id)\
            .order_by(Vote.vote_cast_time.desc())\
            .limit(10)\
            .all()
        
        activity = []
        for vote in recent_votes:
            activity.append({
                'type': 'vote_cast',
                'title': f'Vote cast in {vote.election.title}',
                'description': f'Vote cast for {vote.ballot.title}',
                'timestamp': vote.vote_cast_time.isoformat(),
                'status': vote.vote_status,
                'election_id': vote.election_id,
                'ballot_id': vote.ballot_id
            })
        
        # Get recent elections (last 5)
        recent_elections = Election.query.filter_by(company_id=company_id)\
            .order_by(Election.created_at.desc())\
            .limit(5)\
            .all()
        
        for election in recent_elections:
            activity.append({
                'type': 'election_created',
                'title': f'Election created: {election.title}',
                'description': f'{election.election_type} election',
                'timestamp': election.created_at.isoformat() if election.created_at else None,
                'status': election.status,
                'election_id': election.id
            })
        
        # Sort by timestamp (most recent first)
        activity.sort(key=lambda x: x['timestamp'] or '', reverse=True)
        
        return jsonify({
            'activities': activity[:15]  # Return top 15 most recent activities
        })
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error in get_recent_activity: {str(e)}")
        return jsonify({
            'activities': []
        })

@dashboard_bp.route('/mobile', methods=['GET'])
@jwt_required()
def get_mobile_dashboard():
    """Mobile-specific endpoint that returns all dashboard data in one request to avoid parallel request issues"""
    try:
        from app.models import Election, Vote, Ballot, VoterRegistration, Voter, User
        from flask_jwt_extended import get_jwt_identity
        
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        company_id = current_user.company_id
        
        # Get voter profile for current user
        voter = Voter.query.filter_by(user_id=current_user.id, company_id=company_id).first()
        
        # Get dashboard stats (copied from stats endpoint)
        total_elections = Election.query.filter_by(company_id=company_id).count()
        active_elections = Election.query.filter_by(company_id=company_id, is_active=True).count()
        
        now = datetime.now(timezone.utc)
        upcoming_elections = Election.query.filter_by(company_id=company_id).filter(
            Election.start_date > now
        ).count()
        completed_elections = Election.query.filter_by(company_id=company_id).filter(
            Election.end_date < now
        ).count()
        
        total_ballots = Ballot.query.filter_by(company_id=company_id).count()
        active_ballots = Ballot.query.join(Election).filter(
            Ballot.company_id == company_id,
            Election.is_active == True
        ).count()
        
        total_votes = Vote.query.filter_by(company_id=company_id).count()
        verified_votes = Vote.query.filter_by(company_id=company_id, vote_status='verified').count()
        counted_votes = Vote.query.filter_by(company_id=company_id, is_counted=True).count()
        
        # Get active elections - fix query to match individual endpoint logic
        active_elections_query = Election.query.filter_by(company_id=company_id).filter(
            and_(
                Election.start_date <= now,
                Election.end_date >= now,
                Election.status == 'active'
            )
        ).all()
        
        # Get upcoming elections (scheduled - draft and published)
        upcoming_elections_query = Election.query.filter_by(company_id=company_id).filter(
            Election.status.in_(['draft', 'published'])
        ).all()
        
        # Get user's voting history if voter profile exists
        vote_history = []
        voter_info = {
            'voter_id': '',
            'verification_level': 'none',
            'is_verified': False
        }
        
        if voter:
            voter_info = {
                'voter_id': voter.voter_id or '',
                'verification_level': voter.verification_level or '',
                'is_verified': bool(voter.is_verified)
            }
            
            # Get user's votes
            votes = Vote.query.join(Election).join(Ballot).filter(
                Vote.voter_id == voter.id,
                Vote.company_id == company_id
            ).order_by(Vote.vote_cast_time.desc()).limit(10).all()
            
            vote_history = [{
                'id': v.id,
                'vote_id': v.vote_id or '',
                'tracking_code': v.tracking_code or '',
                'election_id': v.election_id,
                'election_title': v.election.title or '',
                'election_type': v.election.election_type or '',
                'ballot_id': v.ballot_id,
                'ballot_title': v.ballot.title or '',
                'position_title': v.ballot.position_title or '',
                'vote_cast_time': v.vote_cast_time.isoformat() if v.vote_cast_time else None,
                'vote_status': v.vote_status or '',
                'processing_status': v.processing_status or '',
                'vote_method': v.vote_method or '',
                'vote_type': v.vote_type or '',
                'is_counted': bool(v.is_counted),
                'is_verified': bool(v.is_verified),
                'verification_level': v.verification_level or '',
                'biometric_verified': bool(v.biometric_verified),
                'device_verified': bool(v.device_verified),
                'identity_verified': bool(v.identity_verified),
                'receipt_generated': bool(v.receipt_generated),
                'receipt_code': v.receipt_code or '',
                'created_at': v.created_at.isoformat() if v.created_at else None
            } for v in votes]
        
        # Combined response with flattened data structure for mobile app
        return jsonify({
            'dashboard_stats': {
                'ballots': {
                    'active': active_ballots,
                    'total': total_ballots
                },
                'elections': {
                    'active': active_elections,
                    'completed': completed_elections,
                    'total': total_elections,
                    'upcoming': upcoming_elections
                },
                'votes': {
                    'counted': counted_votes,
                    'total': total_votes,
                    'verified': verified_votes
                }
            },
            'active_elections': [{
                'id': e.id,
                'title': e.title or '',
                'description': e.description or '',
                'election_code': e.election_code or '',
                'election_type': e.election_type or '',
                'election_category': e.election_category or '',
                'start_date': e.start_date.isoformat() if e.start_date else None,
                'end_date': e.end_date.isoformat() if e.end_date else None,
                'registration_deadline': e.registration_deadline.isoformat() if e.registration_deadline else None,
                'status': e.status or '',
                'is_public': bool(e.is_public),
                'is_test_election': bool(e.is_test_election),
                'is_active': bool(e.is_active),
                'voting_window_status': e.voting_window_status or '',
                'total_registered_voters': getattr(e, 'total_registered_voters', 0) or 0,
                'total_votes_cast': getattr(e, 'total_votes_cast', 0) or 0,
                'turnout_percentage': float(getattr(e, 'turnout_percentage', 0.0) or 0.0),
                'results_published': bool(getattr(e, 'results_published', False)),
                'created_at': e.created_at.isoformat() if e.created_at else None,
                'updated_at': e.updated_at.isoformat() if e.updated_at else None
            } for e in active_elections_query],
            'upcoming_elections': [{
                'id': e.id,
                'title': e.title or '',
                'description': e.description or '',
                'election_code': e.election_code or '',
                'election_type': e.election_type or '',
                'election_category': e.election_category or '',
                'start_date': e.start_date.isoformat() if e.start_date else None,
                'end_date': e.end_date.isoformat() if e.end_date else None,
                'registration_deadline': e.registration_deadline.isoformat() if e.registration_deadline else None,
                'status': e.status or '',
                'is_public': bool(e.is_public),
                'is_test_election': bool(e.is_test_election),
                'voting_window_status': e.voting_window_status or '',
                'total_registered_voters': getattr(e, 'total_registered_voters', 0) or 0,
                'total_votes_cast': getattr(e, 'total_votes_cast', 0) or 0,
                'turnout_percentage': float(getattr(e, 'turnout_percentage', 0.0) or 0.0),
                'results_published': bool(getattr(e, 'results_published', False)),
                'is_active': bool(e.is_active),
                'created_at': e.created_at.isoformat() if e.created_at else None,
                'updated_at': e.updated_at.isoformat() if e.updated_at else None
            } for e in upcoming_elections_query],
            'voting_history': vote_history,
            'voter_info': voter_info,
            'vote_summary': {
                'total_votes_cast': len(vote_history),
                'verified_votes': sum(1 for v in vote_history if v.get('is_verified')),
                'counted_votes': sum(1 for v in vote_history if v.get('is_counted')),
                'pending_votes': sum(1 for v in vote_history if v.get('processing_status') == 'pending'),
                'elections_participated': len(set(v.get('election_id') for v in vote_history))
            }
        })
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error in get_mobile_dashboard: {str(e)}")
        return jsonify({
            'dashboard_stats': {
                'ballots': {'active': 0, 'total': 0},
                'elections': {'active': 0, 'completed': 0, 'total': 0, 'upcoming': 0},
                'votes': {'counted': 0, 'total': 0, 'verified': 0}
            },
            'active_elections': [],
            'upcoming_elections': [],
            'voting_history': [],
            'voter_info': {'voter_id': '', 'verification_level': 'none', 'is_verified': False},
            'vote_summary': {
                'total_votes_cast': 0,
                'verified_votes': 0,
                'counted_votes': 0,
                'pending_votes': 0,
                'elections_participated': 0
            }
        })