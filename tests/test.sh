#!/bin/bash

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to handle failures
handle_failure() {
    echo -e "${RED}Test failed or was interrupted. Cleaning up...${NC}"
    docker-compose -f docker-compose.tests.yml down > /dev/null 2>&1
    exit 1
}

# Setup error handling
trap handle_failure SIGINT ERR

# Start up databases with Docker Compose
echo -e "${GREEN}Starting database containers...${NC}"
docker-compose -f docker-compose.tests.yml up -d

# Wait for databases to be fully ready (optional delay for database readiness)
echo -e "${GREEN}Waiting for databases to become ready...${NC}"
sleep 10  # Adjust sleep as necessary for your database setup time
# Wait for keycloak to be ready
echo -e "${GREEN}Waiting for Keycloak to become ready...${NC}"
sleep 10  # Adjust sleep as necessary for your database setup time

# Obtain admin access token from Keycloak
KEYCLOAK_URL="http://localhost:8081"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="admin"
echo -e "${GREEN}Obtaining Keycloak admin token...${NC}"
TOKEN_RESPONSE=$(curl --location --request POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
    --header "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "username=${ADMIN_USERNAME}" \
    --data-urlencode "password=${ADMIN_PASSWORD}" \
    --data-urlencode "grant_type=password" \
    --data-urlencode "client_id=admin-cli")

echo "Token Response: $TOKEN_RESPONSE"

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

CLIENT_ID="wingetty-test-client"
export OIDC_CLIENT_ID=$CLIENT_ID


# Create client
RESPONSE=$(curl --location --request POST "${KEYCLOAK_URL}/admin/realms/master/clients" \
    --header "Authorization: Bearer ${ACCESS_TOKEN}" \
    --header "Content-Type: application/json" \
    --data '{
        "clientId": "'$CLIENT_ID'",
        "enabled": true,
        "redirectUris": [
            "http://localhost:5001/authorize/oidc"
        ],
        "protocol": "openid-connect",
        "publicClient": false,
        "baseUrl": "http://localhost:5001",
        "adminUrl": "http://localhost:5001",
        "webOrigins": ["*"]
    }')

# Get the client-secret
# Extract client UUID by filtering the list of clients by clientId
echo -e "${GREEN}Retrieving client UUID...${NC}"
CLIENTS_LIST=$(curl --location --request GET "${KEYCLOAK_URL}/admin/realms/master/clients?clientId=${CLIENT_ID}" \
    --header "Authorization: Bearer ${ACCESS_TOKEN}" \
    --header "Content-Type: application/json")


CLIENT_UUID=$(echo $CLIENTS_LIST | python3 -c "import sys, json; print([client['id'] for client in json.load(sys.stdin) if client['clientId'] == '${CLIENT_ID}'][0])")

echo "Client UUID: $CLIENT_UUID"

# Get the client secret
echo -e "${GREEN}Retrieving client secret...${NC}"
CLIENT_SECRET_RESPONSE=$(curl --location --request GET "${KEYCLOAK_URL}/admin/realms/master/clients/${CLIENT_UUID}/client-secret" \
    --header "Authorization: Bearer ${ACCESS_TOKEN}" \
    --header "Content-Type: application/json")

CLIENT_SECRET=$(echo $CLIENT_SECRET_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['value'])")

echo "Client Secret: $CLIENT_SECRET"
# Set the client secret as an environment variable
export OIDC_CLIENT_SECRET=$CLIENT_SECRET

# Export keycloak well known configuration
export OIDC_SERVER_METADATA_URL="${KEYCLOAK_URL}/realms/master/.well-known/openid-configuration"


if [ "$TOKEN" == "null" ]; then
    echo -e "${RED}Failed to get admin token.${NC}"
    handle_failure
fi

# Run the tests
echo -e "${GREEN}Running tests...${NC}"
# Run pytest with outputting test names
pytest -v

# Capture the status code of pytest
TEST_STATUS=$?

# Tear down the environment
echo -e "${GREEN}Tearing down database containers...${NC}"
docker-compose -f docker-compose.tests.yml down > /dev/null 2>&1

# Exit with the status from pytest or any prior command that failed
if [ $TEST_STATUS -ne 0 ]; then
    echo -e "${RED}Tests failed. See the output above for details.${NC}"
    exit $TEST_STATUS
else
    echo -e "${GREEN}Tests passed successfully.${NC}"
fi

exit 0
