/**
 * Custom Prompts Manager for Claude Desktop Integration
 * Manages user-defined prompts with persistent localStorage storage
 */

// Default prompts that come pre-loaded
const DEFAULT_PROMPTS = [
    {
        id: 'default-1',
        icon: '🤔',
        label: 'Explain This Code',
        prompt: 'I am in a coding interview. Use the provided screenshot to analyze the code shown. Explain in simple, easy-to-understand terms what the code is doing, its main purpose, and how it works. Structure the explanation as a few clear bullet points.',
        action: 'capture'
    },
    {
        id: 'default-2',
        icon: '🐞',
        label: 'Find Bugs',
        prompt: 'I am in a coding interview. Use the provided screenshot to analyze the code shown. Identify potential bugs, logical errors, or race conditions. Provide a bullet-point list of the issues and explain clearly why each one is problematic.',
        action: 'capture'
    },
    {
        id: 'default-3',
        icon: '✨',
        label: 'Suggest Improvements',
        prompt: 'I am in a coding interview. Use the provided screenshot to analyze the code shown. Suggest 3-4 key improvements focusing on readability, performance, and best practices. Provide a bullet-point list of suggestions with brief justifications.',
        action: 'capture'
    },
    {
        id: 'default-4',
        icon: '♻️',
        label: 'Refactor This Code',
        prompt: 'I am in a coding interview. Use the provided screenshot to analyze the code shown. Provide a refactored version of the code that is cleaner and more idiomatic. After the code block, briefly explain the key changes you made and why they are improvements.',
        action: 'capture'
    },
    {
        id: 'default-5',
        icon: '🧪',
        label: 'Write Unit Tests',
        prompt: 'I am in a coding interview. Use the provided screenshot to analyze the code shown. Write a concise set of unit tests for this code. Cover the main logic, at least two important edge cases, and provide comments explaining what each test case is verifying.',
        action: 'capture'
    },
    {
        id: 'default-6',
        icon: '✍️',
        label: 'Write Code from Transcript',
        prompt: 'I am in a coding interview. Based on the following transcript, write the complete code file that fulfills the request. The code should be clean, well-structured, and include comments for complex logic. Provide the full, ready-to-use file content, not just a snippet.',
        action: 'copy'
    },
    {
        id: 'default-7',
        icon: '🎯',
        label: 'Analyze Transcript for Plan',
        prompt: 'I am in a coding interview. Based on the following transcript, what is the primary goal? Create a concise, step-by-step plan for me to follow to implement the feature or fix the bug. Format the output as a simple checklist.',
        action: 'copy'
    },
    {
        id: 'default-8',
        icon: '🗣️',
        label: 'Prep for Behavioral Question',
        prompt: 'I am in a coding interview. The interviewer just asked the question(s) in the transcript below. Generate 3-5 concise, tactical talking points to help me structure my answer effectively. Format them as bullet points starting with action verbs.',
        action: 'copy'
    },
    {
        id: 'default-9',
        icon: '⏱️',
        label: 'Analyze Complexity',
        prompt: 'I am in a coding interview. Use the provided screenshot to analyze the code shown. What is the time and space complexity (Big O notation) of this code? Provide a brief, easy-to-understand explanation for your answer.',
        action: 'capture'
    },
    {
        id: 'default-10',
        icon: '❓',
        label: 'Suggest Follow-up Questions',
        prompt: 'I am in a coding interview and just finished discussing the code in the screenshot. What are 2-3 insightful follow-up questions I could ask the interviewer about the code or related architecture to show my curiosity and deeper understanding?',
        action: 'capture'
    },
    {
        id: 'default-11',
        icon: '📚',
        label: 'Generate Documentation',
        prompt: 'I am in a coding interview. Use the provided screenshot to generate a clear and concise documentation block (like JSDoc, Python Docstring, etc.) for the function or class shown. Include a brief description, parameters, and what it returns.',
        action: 'capture'
    }
];

class CustomPromptsManager {
    constructor() {
        this.prompts = [];
        this.loadPrompts();
    }

    // Load prompts from localStorage or use defaults
    loadPrompts() {
        try {
            const stored = localStorage.getItem('customPrompts');
            if (stored) {
                this.prompts = JSON.parse(stored);
            } else {
                // First time - load defaults
                this.prompts = [...DEFAULT_PROMPTS];
                this.savePrompts();
            }
        } catch (error) {
            console.error('Error loading prompts:', error);
            this.prompts = [...DEFAULT_PROMPTS];
        }
    }

    // Save prompts to localStorage
    savePrompts() {
        try {
            localStorage.setItem('customPrompts', JSON.stringify(this.prompts));
        } catch (error) {
            console.error('Error saving prompts:', error);
        }
    }

    // Get all prompts
    getAllPrompts() {
        return this.prompts;
    }

    // Add a new prompt
    addPrompt(icon, label, prompt, action) {
        const newPrompt = {
            id: 'custom-' + Date.now(),
            icon: icon || '📝',
            label: label,
            prompt: prompt,
            action: action || 'copy'
        };
        this.prompts.push(newPrompt);
        this.savePrompts();
        return newPrompt;
    }

    // Update an existing prompt
    updatePrompt(id, icon, label, prompt, action) {
        const index = this.prompts.findIndex(p => p.id === id);
        if (index !== -1) {
            this.prompts[index] = {
                id: id,
                icon: icon || '📝',
                label: label,
                prompt: prompt,
                action: action || 'copy'
            };
            this.savePrompts();
            return true;
        }
        return false;
    }

    // Delete a prompt
    deletePrompt(id) {
        const index = this.prompts.findIndex(p => p.id === id);
        if (index !== -1) {
            this.prompts.splice(index, 1);
            this.savePrompts();
            return true;
        }
        return false;
    }

    // Reset to default prompts
    resetToDefaults() {
        this.prompts = [...DEFAULT_PROMPTS];
        this.savePrompts();
    }

    // Get a single prompt by ID
    getPrompt(id) {
        return this.prompts.find(p => p.id === id);
    }
}

// Global instance
const promptsManager = new CustomPromptsManager();

// UI Functions
function renderPrompts() {
    const promptsList = document.getElementById('promptsList');
    const prompts = promptsManager.getAllPrompts();

    if (prompts.length === 0) {
        promptsList.innerHTML = '<div class="no-prompts">No prompts yet. Click "+ Add Prompt" to create one.</div>';
        return;
    }

    promptsList.innerHTML = prompts.map(prompt => `
        <div class="prompt-card" data-id="${prompt.id}">
            <div class="prompt-info">
                <div class="prompt-header-row">
                    <span class="prompt-icon">${prompt.icon}</span>
                    <span class="prompt-label">${escapeHtml(prompt.label)}</span>
                </div>
                <div class="prompt-text">${escapeHtml(prompt.prompt)}</div>
            </div>
            <div class="prompt-actions">
                <button class="prompt-action-btn copy-btn" onclick="handlePromptClick('${prompt.id}')" title="Send prompt to Gemini">
                    📋
                </button>
                <button class="prompt-action-btn system-prompt-btn" onclick="applyAsSystemPrompt('${prompt.id}')" title="Apply to selected transcripts">
                    🎯
                </button>
                <button class="prompt-action-btn edit-btn" onclick="editPrompt('${prompt.id}')" title="Edit">
                    ✏️
                </button>
                <button class="prompt-action-btn delete-btn" onclick="deletePrompt('${prompt.id}')" title="Delete">
                    🗑️
                </button>
            </div>
        </div>
    `).join('');
}

function togglePrompts() {
    const content = document.getElementById('promptsContent');
    const toggle = document.getElementById('promptsToggle');

    if (content.classList.contains('expanded')) {
        content.classList.remove('expanded');
        toggle.textContent = '▼';
    } else {
        content.classList.add('expanded');
        toggle.textContent = '▲';
    }
}

async function handlePromptClick(id) {
    const prompt = promptsManager.getPrompt(id);
    if (!prompt) return;

    if (prompt.action === 'capture') {
        // New "Capture" behavior
        console.log(`Triggering screenshot for prompt: "${prompt.label}"`);
        // Store the prompt text so the capture handler can find it
        window.sessionStorage.setItem('analysisPrompt', prompt.prompt);
        // Start the screenshot process
        window.electronAPI.startScreenshot();
    } else {
        // New "Send Text" behavior for prompts with 'copy' action
        console.log(`Sending text prompt: "${prompt.label}"`);
        if (ws && ws.readyState === WebSocket.OPEN) {
            const message = {
                type: 'analyze_text_prompt',
                prompt: prompt.prompt
            };
            ws.send(JSON.stringify(message));
            showNotification('✓ Prompt sent to Gemini!');
        } else {
            console.error('WebSocket not connected. Cannot send prompt.');
            showNotification('❌ WebSocket not connected.');
        }
    }
}

function showAddPromptModal() {
    showPromptModal(null);
}

function editPrompt(id) {
    const prompt = promptsManager.getPrompt(id);
    if (prompt) {
        showPromptModal(prompt);
    }
}

function deletePrompt(id) {
    if (confirm('Are you sure you want to delete this prompt?')) {
        promptsManager.deletePrompt(id);
        renderPrompts();
    }
}

function resetToDefaults() {
    if (confirm('Reset all prompts to defaults? This will delete your custom prompts.')) {
        promptsManager.resetToDefaults();
        renderPrompts();
        showNotification('✓ Prompts reset to defaults');
    }
}

function showPromptModal(prompt) {
    const isEdit = prompt !== null;
    const modal = document.getElementById('promptModal');
    const modalTitle = document.getElementById('modalTitle');
    const iconInput = document.getElementById('promptIcon');
    const labelInput = document.getElementById('promptLabel');
    const promptInput = document.getElementById('promptText');
    const actionInput = document.getElementById('promptAction');

    modalTitle.textContent = isEdit ? '✏️ Edit Prompt' : '➕ Add New Prompt';
    iconInput.value = isEdit ? prompt.icon : '📝';
    labelInput.value = isEdit ? prompt.label : '';
    promptInput.value = isEdit ? prompt.prompt : '';
    actionInput.value = isEdit ? prompt.action : 'copy';

    modal.dataset.editId = isEdit ? prompt.id : '';
    modal.classList.add('show');
}

function closePromptModal() {
    const modal = document.getElementById('promptModal');
    modal.classList.remove('show');
}

function savePromptFromModal() {
    const modal = document.getElementById('promptModal');
    const icon = document.getElementById('promptIcon').value.trim() || '📝';
    const label = document.getElementById('promptLabel').value.trim();
    const prompt = document.getElementById('promptText').value.trim();
    const action = document.getElementById('promptAction').value;

    if (!label) {
        alert('Please enter a label for the prompt');
        return;
    }

    if (!prompt) {
        alert('Please enter the prompt text');
        return;
    }

    const editId = modal.dataset.editId;
    if (editId) {
        // Edit existing
        promptsManager.updatePrompt(editId, icon, label, prompt, action);
        showNotification('✓ Prompt updated');
    } else {
        // Add new
        promptsManager.addPrompt(icon, label, prompt, action);
        showNotification('✓ Prompt added');
    }

    renderPrompts();
    closePromptModal();
}

function applyAsSystemPrompt(promptId) {
    const prompt = promptsManager.getPrompt(promptId);
    if (!prompt) {
        console.error('Prompt not found:', promptId);
        return;
    }

    // Get all selected transcript segments
    const checkboxes = document.querySelectorAll('.transcript-checkbox:checked');
    if (checkboxes.length === 0) {
        showNotification('⚠️ No transcripts selected!');
        return;
    }

    // Collect selected transcript texts
    const selectedTranscripts = [];
    checkboxes.forEach(checkbox => {
        const segmentId = checkbox.dataset.segmentId;
        const segment = transcriptSegments.find(s => s.id === segmentId);
        if (segment) {
            selectedTranscripts.push(`[${segment.speaker}]: ${segment.text}`);
        }
    });

    if (selectedTranscripts.length === 0) {
        showNotification('⚠️ Could not find transcript data!');
        return;
    }

    // Combine system prompt with selected transcripts
    const combinedText = `${prompt.prompt}\n\n---\n\n${selectedTranscripts.join('\n\n')}`;

    console.log('Applying system prompt to selected transcripts...');
    if (ws && ws.readyState === WebSocket.OPEN) {
        const message = {
            type: 'gemini_coach_request',
            text: combinedText
        };
        ws.send(JSON.stringify(message));
        showNotification('✓ Request sent to Gemini!');

        // Uncheck all checkboxes
        checkboxes.forEach(cb => cb.checked = false);
    } else {
        console.error('WebSocket not connected. Cannot send request.');
        showNotification('❌ WebSocket not connected.');
    }
}

function showNotification(text) {
    const notification = document.createElement('div');
    notification.className = 'prompt-notification';
    notification.textContent = text;
    document.body.appendChild(notification);

    setTimeout(() => {
        if (notification.parentNode) {
            document.body.removeChild(notification);
        }
    }, 2000);
}

// Helper function (defined elsewhere but needed here)
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize prompts on page load
document.addEventListener('DOMContentLoaded', () => {
    renderPrompts();
});
