@test "get-id in non-default region" {
  result=$(aws cognito-identity create-identity-pool --identity-pool-name mypool --allow-unauthenticated-identities --endpoint-url http://localhost:5000 --region us-west-2 --output json)
  echo $result

  id=$(echo $result | jq -r '.IdentityPoolId')
  echo $id
  aws cognito-identity get-id --identity-pool-id $id --endpoint-url http://localhost:5000 --region us-west-2
}
