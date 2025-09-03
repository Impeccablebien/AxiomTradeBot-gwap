"""
Event Manager for AxiomTradingBot
Handles event-driven communication between components
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class EventType(Enum):
    """Event types for the bot"""
    NEW_TOKEN = "new_token"
    PRICE_UPDATE = "price_update"
    WALLET_TRANSACTION = "wallet_transaction"
    TRADE_EXECUTED = "trade_executed"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    ERROR_OCCURRED = "error_occurred"
    STRATEGY_STARTED = "strategy_started"
    STRATEGY_STOPPED = "strategy_stopped"
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"

@dataclass
class Event:
    """Represents an event in the system"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime
    source: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow()

class EventManager:
    """
    Manages event subscriptions and publishing for the bot
    """
    
    def __init__(self):
        """Initialize EventManager"""
        self.logger = logging.getLogger("EventManager")
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_queue = asyncio.Queue()
        self._processing = False
        
    async def start(self):
        """Start the event processing loop"""
        if self._processing:
            self.logger.warning("EventManager is already running")
            return
            
        self.logger.info("Starting EventManager")
        self._processing = True
        
        # Start the event processing task
        asyncio.create_task(self._process_events())
        
    async def stop(self):
        """Stop the event processing"""
        self.logger.info("Stopping EventManager")
        self._processing = False
        
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """
        Subscribe to an event type
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
            
        self._subscribers[event_type].append(callback)
        self.logger.debug(f"Subscribed to {event_type.value}")
        
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """
        Unsubscribe from an event type
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to remove from subscribers
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                self.logger.debug(f"Unsubscribed from {event_type.value}")
            except ValueError:
                self.logger.warning(f"Callback not found in {event_type.value} subscribers")
                
    async def publish(self, event_type: EventType, data: Dict[str, Any], source: str = ""):
        """
        Publish an event
        
        Args:
            event_type: Type of event
            data: Event data
            source: Source of the event
        """
        event = Event(
            event_type=event_type,
            data=data,
            timestamp=datetime.utcnow(),
            source=source
        )
        
        await self._event_queue.put(event)
        self.logger.debug(f"Published {event_type.value} event from {source}")
        
    async def _process_events(self):
        """Process events from the queue"""
        while self._processing:
            try:
                # Wait for an event with timeout
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._handle_event(event)
                
            except asyncio.TimeoutError:
                # Continue processing
                continue
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
                await asyncio.sleep(1)
                
    async def _handle_event(self, event: Event):
        """Handle a single event"""
        try:
            subscribers = self._subscribers.get(event.event_type, [])
            
            if not subscribers:
                self.logger.debug(f"No subscribers for {event.event_type.value}")
                return
                
            self.logger.debug(f"Handling {event.event_type.value} event for {len(subscribers)} subscribers")
            
            # Call all subscribers
            tasks = []
            for callback in subscribers:
                try:
                    # Check if callback is async
                    if asyncio.iscoroutinefunction(callback):
                        tasks.append(callback(event))
                    else:
                        # Run sync callback in thread pool
                        loop = asyncio.get_event_loop()
                        tasks.append(loop.run_in_executor(None, callback, event))
                        
                except Exception as e:
                    self.logger.error(f"Error preparing callback for {event.event_type.value}: {e}")
                    
            # Wait for all callbacks to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            self.logger.error(f"Error handling event {event.event_type.value}: {e}")
            
    def get_subscriber_count(self, event_type: EventType) -> int:
        """Get number of subscribers for an event type"""
        return len(self._subscribers.get(event_type, []))
        
    def get_all_event_types(self) -> List[EventType]:
        """Get all event types that have subscribers"""
        return list(self._subscribers.keys())
        
    async def wait_for_event(self, event_type: EventType, timeout: float = None) -> Event:
        """
        Wait for a specific event type
        
        Args:
            event_type: Event type to wait for
            timeout: Maximum time to wait (None for no timeout)
            
        Returns:
            Event object when received
            
        Raises:
            asyncio.TimeoutError: If timeout is reached
        """
        event_received = asyncio.Event()
        received_event = None
        
        def callback(event: Event):
            nonlocal received_event
            received_event = event
            event_received.set()
            
        # Subscribe temporarily
        self.subscribe(event_type, callback)
        
        try:
            # Wait for the event
            await asyncio.wait_for(event_received.wait(), timeout=timeout)
            return received_event
            
        finally:
            # Unsubscribe
            self.unsubscribe(event_type, callback)
            
    async def publish_new_token(self, token_data: Dict[str, Any], source: str = ""):
        """Convenience method for publishing new token events"""
        await self.publish(EventType.NEW_TOKEN, token_data, source)
        
    async def publish_price_update(self, token_address: str, price_data: Dict[str, Any], source: str = ""):
        """Convenience method for publishing price update events"""
        data = {
            "token_address": token_address,
            **price_data
        }
        await self.publish(EventType.PRICE_UPDATE, data, source)
        
    async def publish_wallet_transaction(self, wallet_address: str, transaction_data: Dict[str, Any], source: str = ""):
        """Convenience method for publishing wallet transaction events"""
        data = {
            "wallet_address": wallet_address,
            **transaction_data
        }
        await self.publish(EventType.WALLET_TRANSACTION, data, source)
        
    async def publish_trade_executed(self, trade_data: Dict[str, Any], source: str = ""):
        """Convenience method for publishing trade execution events"""
        await self.publish(EventType.TRADE_EXECUTED, trade_data, source)
        
    async def publish_position_opened(self, position_data: Dict[str, Any], source: str = ""):
        """Convenience method for publishing position opened events"""
        await self.publish(EventType.POSITION_OPENED, position_data, source)
        
    async def publish_position_closed(self, position_data: Dict[str, Any], source: str = ""):
        """Convenience method for publishing position closed events"""
        await self.publish(EventType.POSITION_CLOSED, position_data, source)
        
    async def publish_error(self, error_data: Dict[str, Any], source: str = ""):
        """Convenience method for publishing error events"""
        await self.publish(EventType.ERROR_OCCURRED, error_data, source)
        
    async def publish_strategy_started(self, strategy_name: str, source: str = ""):
        """Convenience method for publishing strategy started events"""
        data = {"strategy_name": strategy_name}
        await self.publish(EventType.STRATEGY_STARTED, data, source)
        
    async def publish_strategy_stopped(self, strategy_name: str, source: str = ""):
        """Convenience method for publishing strategy stopped events"""
        data = {"strategy_name": strategy_name}
        await self.publish(EventType.STRATEGY_STOPPED, data, source)
        
    async def publish_bot_started(self, source: str = ""):
        """Convenience method for publishing bot started events"""
        await self.publish(EventType.BOT_STARTED, {}, source)
        
    async def publish_bot_stopped(self, source: str = ""):
        """Convenience method for publishing bot stopped events"""
        await self.publish(EventType.BOT_STOPPED, {}, source)
