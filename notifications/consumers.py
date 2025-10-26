import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Notification

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.user = self.scope["user"]
            self.notification_group_name = f'user_{self.user.id}_notifications'
            
            # Join the notification group
            await self.channel_layer.group_add(
                self.notification_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            # Send any unread notifications to the client
            await self.send_unread_notifications()
            
            # Update user's last activity
            await self.update_user_activity()

    async def disconnect(self, close_code):
        # Leave the notification group
        await self.channel_layer.group_discard(
            self.notification_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages
        """
        try:
            data = json.loads(text_data)
            
            # Handle different message types
            message_type = data.get('type', '')
            
            if message_type == 'mark_as_read':
                await self.mark_notification_as_read(data.get('notification_id'))
            elif message_type == 'mark_all_as_read':
                await self.mark_all_notifications_as_read()
            elif message_type == 'delete_notification':
                await self.delete_notification(data.get('notification_id'))
            elif message_type == 'ping':
                # Send pong response to keep connection alive
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def notification_message(self, event):
        """
        Send notification messages to WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))

    async def send_unread_notifications(self):
        """
        Send all unread notifications to the connected client
        """
        try:
            unread_notifications = await self.get_unread_notifications()
            
            for notification in unread_notifications:
                await self.send(text_data=json.dumps({
                    'type': 'notification',
                    'notification': notification
                }))
                
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Failed to send notifications: {str(e)}'
            }))

    @database_sync_to_async
    def get_unread_notifications(self):
        """
        Get unread notifications for the user
        """
        notifications = Notification.objects.filter(
            user=self.user,
            is_read=False
        ).order_by('-created_at')[:50]  # Limit to last 50 notifications
        
        return [
            {
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat(),
                'data': notification.data or {}
            }
            for notification in notifications
        ]

    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        """
        Mark a specific notification as read
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=self.user,
                is_read=False
            )
            notification.is_read = True
            notification.save()
            
            return True
        except Notification.DoesNotExist:
            return False

    @database_sync_to_async
    def mark_all_notifications_as_read(self):
        """
        Mark all notifications as read for the user
        """
        Notification.objects.filter(
            user=self.user,
            is_read=False
        ).update(is_read=True)

    @database_sync_to_async
    def delete_notification(self, notification_id):
        """
        Delete a specific notification
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=self.user
            )
            notification.delete()
            return True
        except Notification.DoesNotExist:
            return False

    @database_sync_to_async
    def update_user_activity(self):
        """
        Update user's last activity timestamp
        """
        try:
            user = User.objects.get(id=self.user.id)
            user.last_activity = timezone.now()
            user.save(update_fields=['last_activity'])
        except User.DoesNotExist:
            pass


class RealtimeMetricsConsumer(AsyncWebsocketConsumer):
    """
    Consumer for real-time dashboard metrics
    """
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.user = self.scope["user"]
            self.metrics_group_name = 'realtime_metrics'
            
            # Join the metrics group
            await self.channel_layer.group_add(
                self.metrics_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            # Send initial metrics
            await self.send_initial_metrics()

    async def disconnect(self, close_code):
        # Leave the metrics group
        await self.channel_layer.group_discard(
            self.metrics_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages for metrics
        """
        try:
            data = json.loads(text_data)
            
            if data.get('type') == 'request_metrics':
                await self.send_updated_metrics()
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def metrics_update(self, event):
        """
        Send metric updates to WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'metrics_update',
            'metrics': event['metrics']
        }))

    async def send_initial_metrics(self):
        """
        Send initial dashboard metrics
        """
        metrics = await self.get_dashboard_metrics()
        await self.send(text_data=json.dumps({
            'type': 'initial_metrics',
            'metrics': metrics
        }))

    async def send_updated_metrics(self):
        """
        Send updated dashboard metrics
        """
        metrics = await self.get_dashboard_metrics()
        await self.send(text_data=json.dumps({
            'type': 'updated_metrics',
            'metrics': metrics
        }))

    @database_sync_to_async
    def get_dashboard_metrics(self):
        """
        Get dashboard metrics based on user role
        """
        user = self.user
        
        # Base metrics available to all users
        metrics = {
            'total_users': User.objects.count(),
            'online_users': User.objects.filter(
                last_activity__gte=timezone.now() - timezone.timedelta(minutes=5)
            ).count(),
            'timestamp': timezone.now().isoformat()
        }
        
        # Role-specific metrics
        if user.role == 'admin':
            # Admin gets all metrics
            metrics.update({
                'total_applications': 0,  # Would be calculated from models
                'active_companies': 0,    # Would be calculated from models
                'active_universities': 0, # Would be calculated from models
                'success_rate': 0         # Would be calculated from models
            })
        elif user.role == 'company':
            # Company gets their specific metrics
            metrics.update({
                'my_applications': 0,     # Would be filtered by company
                'my_active_interns': 0,   # Would be filtered by company
                'my_completion_rate': 0   # Would be calculated for company
            })
        elif user.role == 'student':
            # Student gets their specific metrics
            metrics.update({
                'my_applications': 0,     # Would be filtered by student
                'my_active_internships': 0,# Would be filtered by student
                'my_progress': 0          # Would be calculated for student
            })
        elif user.role == 'university':
            # University gets their specific metrics
            metrics.update({
                'my_students': 0,         # Would be filtered by university
                'my_active_internships': 0,# Would be filtered by university
                'my_success_rate': 0      # Would be calculated for university
            })
        
        return metrics


class CollaborationConsumer(AsyncWebsocketConsumer):
    """
    Consumer for real-time collaboration features
    """
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.user = self.scope["user"]
            self.collaboration_group_name = f'collaboration_{self.user.id}'
            
            # Join the collaboration group
            await self.channel_layer.group_add(
                self.collaboration_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            # Send online status
            await self.send_user_status('online')

    async def disconnect(self, close_code):
        # Send offline status
        await self.send_user_status('offline')
        
        # Leave the collaboration group
        await self.channel_layer.group_discard(
            self.collaboration_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages for collaboration
        """
        try:
            data = json.loads(text_data)
            
            message_type = data.get('type', '')
            
            if message_type == 'typing_indicator':
                await self.handle_typing_indicator(data)
            elif message_type == 'file_upload':
                await self.handle_file_upload(data)
            elif message_type == 'video_call':
                await self.handle_video_call(data)
            elif message_type == 'screen_share':
                await self.handle_screen_share(data)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def handle_typing_indicator(self, data):
        """
        Handle typing indicators in chat
        """
        target_user_id = data.get('target_user_id')
        is_typing = data.get('is_typing', False)
        
        if target_user_id:
            await self.send_to_user(target_user_id, {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing
            })

    async def handle_file_upload(self, data):
        """
        Handle file upload notifications
        """
        target_user_id = data.get('target_user_id')
        file_info = data.get('file_info', {})
        
        if target_user_id:
            await self.send_to_user(target_user_id, {
                'type': 'file_upload',
                'user_id': self.user.id,
                'username': self.user.username,
                'file_info': file_info,
                'timestamp': timezone.now().isoformat()
            })

    async def handle_video_call(self, data):
        """
        Handle video call invitations
        """
        target_user_id = data.get('target_user_id')
        call_info = data.get('call_info', {})
        
        if target_user_id:
            await self.send_to_user(target_user_id, {
                'type': 'video_call',
                'user_id': self.user.id,
                'username': self.user.username,
                'call_info': call_info,
                'timestamp': timezone.now().isoformat()
            })

    async def handle_screen_share(self, data):
        """
        Handle screen share invitations
        """
        target_user_id = data.get('target_user_id')
        share_info = data.get('share_info', {})
        
        if target_user_id:
            await self.send_to_user(target_user_id, {
                'type': 'screen_share',
                'user_id': self.user.id,
                'username': self.user.username,
                'share_info': share_info,
                'timestamp': timezone.now().isoformat()
            })

    async def send_user_status(self, status):
        """
        Broadcast user status change
        """
        # Send to all connected users (or specific groups based on implementation)
        await self.channel_layer.group_send(
            'user_status_updates',
            {
                'type': 'user_status_update',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': status,
                'timestamp': timezone.now().isoformat()
            }
        )

    async def send_to_user(self, target_user_id, message_data):
        """
        Send a message to a specific user
        """
        target_group_name = f'user_{target_user_id}_notifications'
        
        await self.channel_layer.group_send(
            target_group_name,
            {
                'type': 'private_message',
                'message': message_data
            }
        )

    async def user_status_update(self, event):
        """
        Handle user status updates
        """
        await self.send(text_data=json.dumps({
            'type': 'user_status_update',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status'],
            'timestamp': event['timestamp']
        }))

    async def private_message(self, event):
        """
        Handle private messages
        """
        await self.send(text_data=json.dumps({
            'type': 'private_message',
            'message': event['message']
        }))
