package moto.tests;

import org.junit.Test;

/**
 * Unit test for simple App.
 */
public class S3Test
{

    @Test
    public void connectToS3() {
        Handler handler = new Handler();
        handler.sendRequest();
    }
}
