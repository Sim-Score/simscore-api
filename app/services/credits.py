from datetime import datetime, timedelta
from typing import List
from fastapi import Request
from app.core.security import db
from app.core.config import settings

class CreditService:
    """
    Manages credit operations and tracking for API usage.
    Handles both authenticated users and guest credits.
    """
    
    @staticmethod
    async def has_sufficient_credits(user_id: str, operations: List[str], num_ideas: int, bytes: int) -> bool:
        """Check if user has enough credits for all requested operations"""
        total_cost = await CreditService.get_total_cost(operations, num_ideas, bytes)
        current_balance = await CreditService.get_credits(user_id)
        return current_balance >= total_cost

    @staticmethod
    async def get_total_cost(operations, num_ideas, bytes):
        costs = [await CreditService.get_operation_cost(operation, num_ideas, bytes) for operation in operations]
        total_cost = sum(costs)
        return total_cost   
    
    @staticmethod
    async def get_credits(user_id: str) -> int:
        """Get available credits for user"""
        credits = db.table('credits').select('balance').eq('user_id', user_id).single().execute()
        return int(credits.data['balance']) if credits.data else 0

    @staticmethod 
    async def deduct_credits(user_id: str, operation: str, data_size: int, bytes: int) -> bool:
        """Deduct credits after successful operation"""
        cost = await CreditService.get_operation_cost(operation, data_size, bytes)
        print(f"Deducting {cost} credits for {operation} with {data_size} statements and a total of {bytes} bytes")
        result = db.rpc(
            'deduct_credits',
            {
                'p_user_id': user_id,
                'amount': cost,
                'operation': operation
            }
        ).execute()
        return result.data

    @staticmethod
    async def get_operation_cost(operation: str, data_size: int, bytes: int) -> int:
        """Calculate credit cost based on operation type and data size"""
        cost_config = settings.OPERATION_COSTS[operation]
        base_cost = cost_config["base_cost"]
        item_cost = data_size / 100 * cost_config["per_hundred_items"]
        byte_cost = bytes / 1024 * cost_config["per_kilobyte"]
        total_cost = int(base_cost + item_cost + byte_cost) # Sum + round it down to next full integer
        print(f"Cost for {operation}: {base_cost} + {item_cost} + {byte_cost} = {total_cost}") 
        return total_cost

    @staticmethod
    async def refresh_daily_credits():
        """Refresh daily credits for all users"""
        # Get users needing refresh
        users = db.table('credits').select('*').lt(
            'last_free_credit_update', 
            datetime.now() - timedelta(days=1)
        ).execute()
        
        for user in users.data:
            if not user.get('is_guest'):
              if user['balance'] >= settings.USER_MAX_CREDITS:
                continue  # The user has paid for more balance, don't change it.
              new_balance = min(
                  user['balance'] + settings.USER_DAILY_CREDITS,
                  settings.MAX_CREDIT_BALANCE
              )
            else:
              new_balance = min(
                  user['balance'] + settings.GUEST_DAILY_CREDITS,
                  settings.GUEST_MAX_CREDITS
              )    
            db.table('credits').update({
                'balance': new_balance,
                'last_free_credit_update': datetime.now()
            }).eq('user_id', user['user_id']).execute()
