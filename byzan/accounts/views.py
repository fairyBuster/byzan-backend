from django.shortcuts import render
import jwt ,datetime
from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import RegisterSerializer,LoginSerializer, ProfileSerializer
from .models import User
from rest_framework import status
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from posts.models import Post

def generate_token(user):
    payload = {
        'user_id': user.id,
        'email': user.email,
        'username': user.username,
        'full_name': user.full_name,
        'phone': user.phone,
        'address': user.address,
        'city': user.city,
        'state': user.state,
        'country': user.country,
        'pincode': user.pincode,
        'balance': float(user.balance) if user.balance is not None else 0.0,
        'exp': datetime.datetime.now() + datetime.timedelta(days=1),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    
class RegisterView(APIView):
    @extend_schema(request=RegisterSerializer)
    @extend_schema(responses={201: None})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token = generate_token(user)
            return Response({
                'msg': 'Registration successful',
                'token': token,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'full_name': user.full_name,
                    'phone': user.phone,
                    'address': user.address,
                    'city': user.city,
                    'state': user.state,
                    'country': user.country,
                    'pincode': user.pincode,
                    'balance': user.balance
                }
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
  
    @extend_schema(request=LoginSerializer)
    @extend_schema(responses={200: None})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            user = authenticate(username=email, password=password)
            if user:
                token = generate_token(user)
                return Response({
                    'msg': 'Login successful',
                    'token': token,
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username,
                        'full_name': user.full_name,
                        'phone': user.phone,
                        'address': user.address,
                        'city': user.city,
                        'state': user.state,
                        'country': user.country,
                        'pincode': user.pincode,
                        'balance': user.balance
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({'msg': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=ProfileSerializer)
    def get(self, request):
        user = request.user
        profile_data = ProfileSerializer(user).data
        stats = {
            'articles_posted': Post.objects.filter(author=user, status='published').count(),
            'reader_rating': 0,
            'books_published': 0,
            'my_library': user.enrollments.count() if hasattr(user, 'enrollments') else 0,
        }
        return Response({**profile_data, **stats}, status=status.HTTP_200_OK)

    @extend_schema(request=ProfileSerializer, responses=ProfileSerializer)
    def patch(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            return Response(ProfileSerializer(user).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=ProfileSerializer, responses=ProfileSerializer)
    def put(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=False)
        if serializer.is_valid():
            user = serializer.save()
            return Response(ProfileSerializer(user).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

