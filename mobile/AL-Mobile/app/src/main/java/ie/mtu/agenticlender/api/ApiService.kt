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

    @POST("applications")
    suspend fun submitApplication(
        @Header("Authorization") auth: String,
        @Body request: ApplicationRequest
    ): Response<ApplicationResponse>
}