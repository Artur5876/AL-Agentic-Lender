package ie.mtu.agenticlender.api

import com.google.gson.Gson
import com.google.gson.JsonParseException

// AL-3 US-111: calls POST /affordability and turns the answer into a simple result.
// Works the same way as ApplicationRepository, so errors look the same everywhere.

sealed interface AffordabilityResult {
    data class Success(val estimate: AffordabilityResponse) : AffordabilityResult
    data class Failure(val message: String) : AffordabilityResult
}

class AffordabilityRepository(
    private val api: ApiService = RetrofitClient.api,
    private val gson: Gson = Gson()
) {
    suspend fun getEstimate(idToken: String, request: AffordabilityRequest): AffordabilityResult {
        val response = api.getAffordability("Bearer $idToken", request)

        if (response.isSuccessful) {
            val estimate = response.body()
                ?: return AffordabilityResult.Failure("The estimate came back empty. Please try again.")
            return AffordabilityResult.Success(estimate)
        }

        // Not successful: read the API's error message (docs/api.md section 4, same shape for every error)
        val errorBody = response.errorBody()?.string()
        val apiError = try {
            errorBody?.let { gson.fromJson(it, ApiErrorResponse::class.java) }?.error
        } catch (_: JsonParseException) {
            null
        }

        // e.g. "Validation failed\ntermYears: must be between 5 and 35"
        val message = apiError?.let { error ->
            buildString {
                append(error.message)
                error.details.orEmpty().forEach { detail ->
                    append("\n${detail.field}: ${detail.message}")
                }
            }
        } ?: "Couldn't get an estimate (error ${response.code()}). Please try again."

        return AffordabilityResult.Failure(message)
    }
}