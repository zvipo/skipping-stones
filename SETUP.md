# Skipping Stones Game - AWS DynamoDB Setup

This guide will help you set up AWS DynamoDB for user state persistence in the Skipping Stones game.

## Prerequisites

1. AWS Account with appropriate permissions
2. Python 3.7+ installed
3. AWS CLI configured (optional but recommended)

## AWS Setup

### 1. Create DynamoDB Table

You can create the DynamoDB table manually in the AWS Console or let the application create it automatically.

**Manual Creation:**
- Go to AWS DynamoDB Console
- Create a new table with the following settings:
  - Table name: `skipping-stones-game-state`
  - Partition key: `user_id` (String)
  - Billing mode: Pay per request

**Automatic Creation:**
The application will automatically create the table if it doesn't exist when you first run it.

### 2. Configure AWS Credentials

You have several options for AWS credentials:

**Option A: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your-access-key-id
export AWS_SECRET_ACCESS_KEY=your-secret-access-key
export AWS_DEFAULT_REGION=us-east-1
```

**Option B: AWS Credentials File**
```bash
aws configure
```

**Option C: IAM Role (for EC2/ECS deployment)**
Attach an IAM role with DynamoDB permissions to your instance.

### 3. Required IAM Permissions

Your AWS credentials need the following DynamoDB permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DescribeTable",
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:DeleteItem",
                "dynamodb:UpdateItem"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/skipping-stones-game-state"
        }
    ]
}
```

## Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-change-this

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/callback

# AWS Configuration (optional if using AWS CLI or IAM roles)
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_DEFAULT_REGION=us-east-1
DYNAMODB_TABLE_NAME=skipping-stones-game-state
```

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables (see above)

3. Run the application:
```bash
python app.py
```

## Features

With AWS DynamoDB integration, the game now supports:

- **Automatic State Saving**: Game state is saved after each move
- **User Progress Tracking**: Completed levels are tracked per user
- **Resume Game**: Users can resume from where they left off
- **Progress Statistics**: Visual progress indicators for completed levels
- **Logout State Preservation**: Game state is saved when users logout

## Data Structure

The DynamoDB table stores the following data for each user:

- `user_id`: Unique user identifier (partition key)
- `current_level`: Current level being played
- `board_state`: JSON representation of the game board
- `move_history`: Array of moves made in the current game
- `marbles_left`: Number of marbles remaining
- `moves_count`: Number of moves made
- `game_status`: Current game status (Playing/Won/Stuck)
- `completed_levels`: Array of completed level IDs
- `last_updated`: Timestamp of last update

## API Endpoints

The following new API endpoints are available:

- `POST /api/game-state/save`: Save current game state
- `GET /api/game-state/load`: Load user's game state
- `POST /api/game-state/complete-level`: Mark level as completed
- `GET /api/user/stats`: Get user statistics

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**: Ensure your AWS credentials are properly configured
2. **DynamoDB Table Not Found**: The application will create the table automatically
3. **Permission Denied**: Check that your AWS credentials have the required DynamoDB permissions

### Debug Mode

Run the application in debug mode to see detailed logs:
```bash
FLASK_ENV=development python app.py
```

## Security Considerations

- Use IAM roles instead of access keys when possible
- Regularly rotate your AWS credentials
- Consider using AWS Secrets Manager for sensitive configuration
- Implement proper error handling for production deployments 