package ie.mtu.agenticlender.api

import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

interface ApiService {

    @GET("health")
    suspend fun health(): Response<ResponseBody>

    @POST("valuations")
    suspend fun createValuation(
        @Header("Authorization") auth: String,
        @Body request: ValuationRequest
    ): Response<ValuationResponse>

    // AL-3 US-111: borrowing estimate from the calculation module (nothing is saved)
    @POST("affordability")
    suspend fun getAffordability(
        @Header("Authorization") auth: String,
        @Body request: AffordabilityRequest
    ): Response<AffordabilityResponse>

    @POST("applications")
    suspend fun submitApplication(
        @Header("Authorization") auth: String,
        @Body request: ApplicationRequest
    ): Response<ApplicationResponse>
}