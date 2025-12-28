import axios from 'axios';
import { getApiBase } from './config';

// Types
/**
 * Interface representing a memory item in the Cipher system.
 * @property id - Unique identifier for the memory.
 * @property category - Category of memory (fact, preference, skill_learned).
 * @property content - The actual memory content, can be string or object.
 * @property context - Optional context data associated with the memory.
 * @property created_at - ISO timestamp of creation.
 */
export interface MemoryItem {
  id: string;
  category: string;
  content: any;
  context?: any;
  created_at: string;
}

/**
 * Interface representing a skill registered in the system.
 * @property id - Unique identifier for the skill.
 * @property name - Display name of the skill.
 * @property description - Description of what the skill does.
 * @property enabled - Whether the skill is currently active.
 * @property parameters - Optional configuration parameters for the skill.
 */
export interface SkillItem {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  parameters?: any;
}

/**
 * Interface representing a response from the QA engine.
 * @property answer - The generated answer text.
 * @property evidence - Array of evidence items used to generate the answer.
 * @property hrm - Optional High-Resolution Modeling metadata.
 * @property error - Optional error message if the request failed.
 */
export interface QAResponse {
  answer: string;
  evidence: any[];
  hrm?: {
    enabled: boolean;
    steps?: number;
  };
  error?: string;
}

const getClient = () => {
    return axios.create({
        baseURL: getApiBase(),
        headers: {
            'Content-Type': 'application/json',
        },
    });
};

/**
 * Central API client for interacting with the backend services.
 * Handles QA, Document Uploads, Memory operations, and Skills management.
 */
export const api = {
    // --- QA & Documents ---
    
    /**
     * Asks a question to the system using the configured QA engine.
     * @param question - The user's question.
     * @param useHrm - Whether to enable High-Resolution Modeling (step-by-step reasoning).
     * @returns A promise resolving to the QA response.
     */
    askQuestion: async (question: string, useHrm: boolean = false): Promise<QAResponse> => {
        try {
            const res = await getClient().post(`/ask?question=${encodeURIComponent(question)}&use_hrm=${useHrm}`);
            return res.data;
        } catch (error: any) {
            console.error("API Error (askQuestion):", error);
            return { answer: "", evidence: [], error: error.message || "Failed to get answer" };
        }
    },

    /**
     * Retrieves extracted facts from the backend.
     * @returns A promise resolving to an array of facts.
     */
    getFacts: async (): Promise<any[]> => {
        try {
            const res = await getClient().get('/facts');
            return res.data;
        } catch (error) {
            console.error("API Error (getFacts):", error);
            return [];
        }
    },

    /**
     * Uploads files and web URLs for processing.
     * @param files - Array of File objects to upload.
     * @param webUrls - Newline or comma-separated list of URLs.
     * @param reportWeek - The reporting week string.
     * @param asyncPdf - Whether to process PDFs asynchronously.
     * @param onProgress - Callback for upload progress percentage.
     * @returns Promise resolving to the upload response.
     */
    uploadFiles: async (
        files: File[] | null, 
        webUrls: string, 
        reportWeek: string, 
        asyncPdf: boolean,
        onProgress?: (percent: number) => void
    ): Promise<any> => {
        const formData = new FormData();
        if (files) {
            files.forEach(f => formData.append('files', f));
        }
        
        webUrls.split(/\n|,/)
               .map(url => url.trim())
               .filter(url => url.length > 0)
               .forEach(url => formData.append('web_urls', url));

        try {
            const res = await getClient().post(
                `/upload?report_week=${encodeURIComponent(reportWeek)}&async_pdf=${asyncPdf}`, 
                formData, 
                {
                    headers: { 'Content-Type': 'multipart/form-data' },
                    onUploadProgress: (progressEvent) => {
                        if (progressEvent.total && onProgress) {
                            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                            onProgress(percent);
                        }
                    }
                }
            );
            return res.data;
        } catch (error) {
            console.error("API Error (uploadFiles):", error);
            throw error;
        }
    },

    /**
     * Triggers the loading of sample data.
     * @param reportWeek - The reporting week for the samples.
     * @param asyncPdf - Whether to process sample PDFs asynchronously.
     * @returns Promise resolving to the response.
     */
    loadSamples: async (reportWeek: string, asyncPdf: boolean): Promise<any> => {
        try {
            const res = await getClient().post(`/load_samples?report_week=${encodeURIComponent(reportWeek)}&async_pdf=${asyncPdf}`);
            return res.data;
        } catch (error) {
           console.error("API Error (loadSamples):", error);
           throw error;
        }
    },

    // --- Cipher Memory ---
    
    /**
     * Adds a new memory item.
     * @param category - The category of the memory.
     * @param content - The content of the memory.
     * @returns Promise resolving to the new memory ID.
     */
    addMemory: async (category: string, content: any): Promise<string> => {
        try {
            // Cipher memory endpoint (backend: /cipher/memory)
            const res = await getClient().post('/cipher/memory', { category, content });
            return res.data.id;
        } catch (error) {
            console.error("API Error (addMemory):", error);
            throw error;
        }
    },

    /**
     * Searches for memory items.
     * @param query - The search query term.
     * @param category - Optional category filter.
     * @returns Promise resolving to an array of matching MemoryItems.
     */
    searchMemory: async (query: string, category?: string): Promise<MemoryItem[]> => {
        try {
            const params = new URLSearchParams();
            if (query) params.append('q', query);
            if (category) params.append('category', category);
            const res = await getClient().get(`/cipher/memory?${params.toString()}`);
            return res.data;
        } catch (error) {
            console.error("API Error (searchMemory):", error);
            return [];
        }
    },

    // --- Skills ---

    /**
     * Retrieves all registered skills.
     * @returns Promise resolving to an array of SkillItems.
     */
    getSkills: async (): Promise<SkillItem[]> => {
        try {
            // Cipher skills endpoint (backend: /cipher/skills)
            const res = await getClient().get('/cipher/skills');
            return res.data;
        } catch (error) {
            console.error("API Error (getSkills):", error);
            return [];
        }
    },

    /**
     * Toggles a skill's enabled state.
     * @param skillId - The ID of the skill to toggle.
     * @param enabled - The desired state.
     * @returns Promise resolving to true if successful, false otherwise.
     */
    toggleSkill: async (skillId: string, enabled: boolean): Promise<boolean> => {
        try {
            // Cipher skills endpoint (backend: /cipher/skills/{id})
            await getClient().put(`/cipher/skills/${skillId}`, { enabled });
            return true;
        } catch (error) {
            console.error("API Error (toggleSkill):", error);
            return false;
        }
    },

    /**
     * Retrieves the A2UI demo definition.
     * @returns Promise resolving to the A2UI component definition array.
     */
    getA2UIDemo: async (): Promise<any[]> => {
        try {
            const res = await getClient().get('/cipher/a2ui/demo');
            return res.data;
        } catch (error) {
            console.error("API Error (getA2UIDemo):", error);
            throw error;
        }
    },

    // --- Model Lab ---

    /**
     * Retrieves all available models from Ollama and TensorZero.
     * @returns Promise resolving to models response with ollama, tensorzero, and services status.
     */
    getModels: async (): Promise<any> => {
        try {
            const res = await getClient().get('/models/');
            return res.data;
        } catch (error) {
            console.error("API Error (getModels):", error);
            return { ollama: [], tensorzero: [], services: { ollama: 'error', tensorzero: 'error' } };
        }
    },

    /**
     * Tests a model by sending a prompt.
     * @param modelName - Name of the model to test.
     * @param provider - "ollama" or "tensorzero".
     * @param prompt - Test prompt.
     * @returns Promise resolving to the model response.
     */
    testModel: async (modelName: string, provider: string, prompt: string): Promise<any> => {
        try {
            const res = await getClient().post(`/models/test/${modelName}?provider=${provider}&prompt=${encodeURIComponent(prompt)}`);
            return res.data;
        } catch (error) {
            console.error("API Error (testModel):", error);
            throw error;
        }
    },

    /**
     * Gets health status of model services.
     * @returns Promise resolving to health status object.
     */
    getModelHealth: async (): Promise<any> => {
        try {
            const res = await getClient().get('/models/health');
            return res.data;
        } catch (error) {
            console.error("API Error (getModelHealth):", error);
            return {
                ollama: { status: 'unreachable', url: 'http://ollama:11434' },
                tensorzero: { status: 'unreachable', url: 'http://tensorzero:3000' }
            };
        }
    }
};
