package moto.tests;

import static moto.tests.DependencyFactory.cognitoIdpClient;
import static org.junit.Assert.*;

import org.junit.Test;
import software.amazon.awssdk.services.cognitoidentityprovider.CognitoIdentityProviderClient;
import software.amazon.awssdk.services.cognitoidentityprovider.model.AssociateSoftwareTokenRequest;
import software.amazon.awssdk.services.cognitoidentityprovider.model.AssociateSoftwareTokenResponse;
import software.amazon.awssdk.services.cognitoidentityprovider.model.AttributeType;
import software.amazon.awssdk.services.cognitoidentityprovider.model.AuthFlowType;
import software.amazon.awssdk.services.cognitoidentityprovider.model.CreateUserPoolRequest;
import software.amazon.awssdk.services.cognitoidentityprovider.model.CreateUserPoolClientRequest;
import software.amazon.awssdk.services.cognitoidentityprovider.model.ConfirmSignUpRequest;
import software.amazon.awssdk.services.cognitoidentityprovider.model.InitiateAuthRequest;
import software.amazon.awssdk.services.cognitoidentityprovider.model.InitiateAuthResponse;
import software.amazon.awssdk.services.cognitoidentityprovider.model.SignUpRequest;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;


public class CognitoIDPTest {

    @Test
    public void testAssociateSoftwareToken() {
        CognitoIdentityProviderClient client = cognitoIdpClient();

        CreateUserPoolRequest up_request = CreateUserPoolRequest.builder()
                .poolName("myfirstuserpool")
                .build();

        String userPoolId = client.createUserPool(up_request).userPool().id();
        System.out.println(userPoolId);

        CreateUserPoolClientRequest upc_request = CreateUserPoolClientRequest.builder()
                .clientName("myfirstuserpoolclient")
                .userPoolId(userPoolId)
                .build();

        String clientId = client.createUserPoolClient(upc_request).userPoolClient().clientId();
        System.out.println(clientId);

        // Create User
        AttributeType userAttrs = AttributeType.builder()
                .name("email")
                .value("test@test.com")
                .build();
        String password = "P@ssw0rdWithTonsOfCharacters";

        List<AttributeType> userAttrsList = new ArrayList<>();
        userAttrsList.add(userAttrs);
        SignUpRequest signUpRequest = SignUpRequest.builder()
                    .userAttributes(userAttrsList)
                    .username("myuser")
                    .clientId(clientId)
                    .password(password)
                    .build();

        client.signUp(signUpRequest);

        ConfirmSignUpRequest confirmSignUpRequest = ConfirmSignUpRequest.builder()
                .clientId(clientId)
                .confirmationCode("code")
                .username("myuser")
                .build();

        client.confirmSignUp(confirmSignUpRequest);

        InitiateAuthResponse initiateAuthResponse = client.initiateAuth(
                InitiateAuthRequest.builder()
                        .authFlow(AuthFlowType.USER_PASSWORD_AUTH)
                        .authParameters(Map.of(
                                "USERNAME", "myuser",
                                "SECRET_HASH", "n/a",
                                "PASSWORD", password))
                        .clientId(clientId)
                        .build());
        String accessToken = initiateAuthResponse.authenticationResult().accessToken();

        AssociateSoftwareTokenRequest softwareTokenRequest = AssociateSoftwareTokenRequest.builder()
                .accessToken(accessToken)
                .build();
        AssociateSoftwareTokenResponse tokenResponse = client
                .associateSoftwareToken(softwareTokenRequest);
        String secretCode = tokenResponse.secretCode();

        assertNotNull(secretCode);
    }
}
