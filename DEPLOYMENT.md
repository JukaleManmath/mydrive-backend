# MyDrive Backend Deployment Guide

## 1. Database Setup (Supabase)

1. Go to https://supabase.com and sign up with GitHub
2. Create a new project:
   - Name: `mydrive`
   - Database Password: Create a strong password
   - Region: Choose closest to your users
   - Plan: Free tier

3. Run the database schema:
   - Go to SQL Editor
   - Copy and paste the contents of `supabase/schema.sql`
   - Click "Run"

4. Get the database connection string:
   - Go to Project Settings > Database
   - Find "Connection string" under "Connection info"
   - Select "URI" format
   - Copy and replace `[YOUR-PASSWORD]` with your database password

## 2. Backend Deployment (Render)

1. Go to https://render.com and sign up with GitHub
2. Create a new Web Service:
   - Connect your GitHub repository
   - Name: `mydrive-backend`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Plan: Free

3. Add Environment Variables:
   ```
   DATABASE_URL=your_supabase_connection_string
   AWS_ACCESS_KEY_ID=your_aws_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret
   AWS_REGION=your_aws_region
   S3_BUCKET_NAME=your_bucket_name
   JWT_SECRET_KEY=your_jwt_secret
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   CORS_ORIGINS=https://your-frontend-domain.vercel.app
   ```

## 3. Testing the Deployment

1. Test the API:
   - Visit `https://your-render-backend-url.onrender.com/docs`
   - Try the authentication endpoints
   - Test file upload/download
   - Verify S3 integration

## 4. Free Tier Limitations

### Supabase
- 500MB database
- 2GB bandwidth
- 50MB file uploads
- 2 million row reads/month

### Render
- 750 hours/month
- 512MB RAM
- Shared CPU
- Sleeps after 15 minutes of inactivity

## 5. Monitoring

1. Supabase Dashboard:
   - Monitor database usage
   - View API requests
   - Check storage usage

2. Render Dashboard:
   - View logs
   - Monitor uptime
   - Check resource usage

## 6. Troubleshooting

1. Database Connection Issues:
   - Verify Supabase connection string
   - Check if IP is allowed in Supabase
   - Verify database credentials

2. Backend Issues:
   - Check Render logs
   - Verify environment variables
   - Test API endpoints

3. S3 Issues:
   - Verify AWS credentials
   - Check bucket permissions
   - Verify CORS configuration 