package ie.mtu.agenticlender.api

import com.google.gson.Gson
import com.google.gson.JsonParseException

sealed interface ApplicationSubmissionResult {
    data class Success(val application: ApplicationResponse) : ApplicationSubmissionResult
    data class Failure(
        val message: String,
        val fieldErrors: Map<String, String> = emptyMap()
    ) : ApplicationSubmissionResult
}

class ApplicationRepository(
    private val api: ApiService = RetrofitClient.api,
    private val gson: Gson = Gson()
) {
    suspend fun submitApplication(
        idToken: String,
        request: ApplicationRequest
    ): ApplicationSubmissionResult {
        val response = api.submitApplication("Bearer $idToken", request)
        if (response.isSuccessful) {
            val application = response.body()
                ?: return ApplicationSubmissionResult.Failure(
                    "Application API returned an empty response."
                )
            return ApplicationSubmissionResult.Success(application)
        }

        val errorBody = response.errorBody()?.string()
        val apiError = try {
            errorBody?.let { gson.fromJson(it, ApiErrorResponse::class.java) }?.error
        } catch (_: JsonParseException) {
            null
        }
        val message = apiError?.let { error ->
            buildString {
                append(error.message)
                error.details.orEmpty().forEach { detail ->
                    append("\n")
                    append(detail.field)
                    append(": ")
                    append(detail.message)
                }
            }
        } ?: "Application API error ${response.code()}: ${errorBody ?: response.message()}"

        val fieldErrors = apiError?.details.orEmpty()
            .associate { detail -> detail.field to detail.message }
        return ApplicationSubmissionResult.Failure(message, fieldErrors)
    }
}
