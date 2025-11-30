# Custom Prompts Guide

The Electron overlay now includes **Custom Prompts** - a powerful system for creating, managing, and using custom prompts with Claude Desktop. You can create your own prompts, edit them, delete them, and they're automatically saved for future sessions!

## How to Use

### Using Prompts
1. **Open the Electron overlay** during your interview
2. **Click on "💬 Custom Prompts for Claude"** to expand the section
3. **Click the 📋 (copy) button** on any prompt to copy it to clipboard
4. **Switch to Claude Desktop** (Alt+Tab)
5. **Paste** (Ctrl+V) and press Enter

You'll see a green notification when the prompt is copied!

### Managing Prompts
- **Add New Prompt**: Click "➕ Add Prompt" button
- **Edit Prompt**: Click the ✏️ (edit) button on any prompt card
- **Delete Prompt**: Click the 🗑️ (delete) button on any prompt card
- **Reset to Defaults**: Click "🔄 Reset to Defaults" to restore the original 5 prompts

All changes are automatically saved to your browser's localStorage and will persist across sessions!

## Default Prompts

The system comes with 5 pre-loaded prompts that you can use, edit, or delete:

### 📄 Review Latest Question
**What it does:** Asks Claude to analyze your most recent captured transcript segment and help you answer the interviewer's question.

**When to use:**
- Right after the interviewer asks a complex question
- When you need help formulating your response
- During a brief pause in the interview

**The prompt:**
```
Look at my latest captured transcript segment and help me craft a strong answer to the interviewer's question.
```

---

### 📚 Review All Segments
**What it does:** Gets Claude to review all your captured transcript segments and provide feedback on how the interview is progressing.

**When to use:**
- During longer breaks
- After answering several questions
- When you want a mid-interview check-in

**The prompt:**
```
Review all my captured transcript segments and give me feedback on how the interview is going so far.
```

---

### 📸 Capture & Analyze Screen
**What it does:** Triggers Claude to capture a screenshot (using the MCP tool) and analyze what's shown.

**When to use:**
- When you're stuck on a coding problem
- Need help with an error message
- Want to share a diagram or whiteboard

**The prompt:**
```
Capture a screenshot of my current screen and help me analyze what's shown.
```

---

### 🎯 Overall Interview Feedback
**What it does:** Requests comprehensive feedback on your entire interview performance with specific areas to focus on.

**When to use:**
- After the interview ends
- During a long break between rounds
- When you want detailed analysis

**The prompt:**
```
Based on all my interview transcript segments, give me detailed feedback on:
1. What I did well
2. What I could improve
3. Any red flags or concerns
4. Overall assessment
```

---

### 💡 How Can I Improve?
**What it does:** Asks for specific, actionable tips to improve your performance in the remaining portion of the interview.

**When to use:**
- Between interview sections
- After a rough question
- When you feel you're struggling

**The prompt:**
```
Review my interview transcripts and give me 3-5 specific, actionable tips for improving my answers in the remaining portion of the interview.
```

---

## Workflow Examples

### Example 1: Quick Question Help
```
1. Interviewer asks: "Design a rate limiter"
2. Transcript captures the question
3. You press Capture button (Ctrl+Shift+C)
4. Click "📄 Review Latest Question"
5. Alt+Tab to Claude Desktop
6. Ctrl+V and Enter
7. Read Claude's suggestions while interviewer waits
8. Answer with confidence!
```

### Example 2: Mid-Interview Check-In
```
1. Interviewer takes a break ("I'll be right back")
2. Click "📚 Review All Segments"
3. Alt+Tab to Claude Desktop
4. Paste and get feedback
5. Claude tells you: "You're doing well on technical depth but could
   add more real-world examples"
6. Adjust your approach for remaining questions
```

### Example 3: Code Debugging Help
```
1. You're stuck on a coding challenge
2. Click "📸 Capture & Analyze Screen"
3. Alt+Tab to Claude Desktop
4. Paste prompt
5. Claude captures screenshot via MCP
6. Claude: "I see the issue on line 42 - you're not handling
   the edge case where..."
7. Fix the issue and continue!
```

## Tips for Best Results

### 📌 Capture Strategically
- Don't capture everything - only important questions
- Use the live buffer to see what's being transcribed
- Capture when you hear a complex or multi-part question

### ⚡ Stay Fast
- Keep Claude Desktop open in another window
- Use Alt+Tab to switch quickly
- Practice the workflow before your real interview

### 🎯 Be Specific
- After pasting a prompt, you can add more context
- Example: "Review latest question - I'm particularly unsure about the scalability aspect"
- The more context you give Claude, the better the help

### 🔄 Iterate
- If Claude's first response isn't enough, ask follow-up questions
- "Can you give me a specific code example?"
- "What's the time complexity of that approach?"

## Creating Custom Prompts

### Adding a New Prompt

1. Click "➕ Add Prompt" in the toolbar
2. Fill in the fields:
   - **Icon**: Enter any emoji (e.g., 🎨, 🚀, 💻)
   - **Label**: Short, descriptive name (e.g., "System Design Help")
   - **Prompt Text**: The actual prompt that will be copied
3. Click "Save"

**Example Custom Prompt:**
- Icon: 🎨
- Label: Code Review Request
- Prompt: "Review the code I just wrote and suggest improvements for: 1) Readability, 2) Performance, 3) Best practices, 4) Potential bugs"

### Editing an Existing Prompt

1. Click the ✏️ (edit) button on the prompt card
2. Modify any field (icon, label, or prompt text)
3. Click "Save"

### Best Practices for Custom Prompts

- **Keep labels short** - They should fit in one line
- **Make prompts specific** - Include numbered lists or clear instructions
- **Use emojis wisely** - Pick icons that help you quickly identify prompts
- **Test your prompts** - Try them with Claude to ensure they work as expected
- **Organize by workflow** - Create prompts for different interview stages

## Keyboard Shortcuts

While Custom Prompts are click-based, here are useful keyboard shortcuts:

- `Ctrl+Shift+C` - Capture current transcript to segment
- `Alt+Tab` - Switch to Claude Desktop
- `Ctrl+V` - Paste the copied prompt
- `Escape` - Close overlay window
- `Escape` (in modal) - Cancel prompt editing

## Best Practices

### ✅ Do:
- Practice the workflow before real interviews
- Keep prompts short and clear
- Capture only important moments
- Use during natural pauses

### ❌ Don't:
- Rely 100% on Claude - use it as a backup
- Capture every single thing said
- Spend too long reading Claude's response
- Forget to adapt Claude's suggestions to your own voice

## Troubleshooting

**"Prompt didn't copy"**
- Make sure the overlay has focus
- Try clicking the 📋 copy button again
- Check if clipboard permissions are enabled

**"My prompts disappeared"**
- Prompts are saved in localStorage
- Check if you accidentally clicked "Reset to Defaults"
- If using private/incognito mode, prompts won't persist

**"Can't edit or delete a prompt"**
- Make sure the prompts section is expanded
- Click the correct button (✏️ for edit, 🗑️ for delete)
- Refresh the overlay if buttons aren't responding

**"Modal won't close"**
- Click the ✕ button in the top-right
- Click "Cancel" button
- Press Escape key
- Click outside the modal

**"Claude doesn't see my transcripts"**
- Verify MCP server is connected (see [MCP_INTEGRATION.md](MCP_INTEGRATION.md))
- Make sure you've captured at least one segment
- Check that `.transcript_history` file exists in `generated_code/`

**"Response too slow"**
- Claude might be analyzing a lot of text
- Consider using "Review Latest" instead of "Review All"
- Make sure your internet connection is stable

## Advanced Usage

### Combining with Coach Mode

You can use **both** systems together:
1. **Gemini Coach Mode** - Real-time suggestions (automatic)
2. **Claude via MCP** - Deep analysis (manual prompts)

Use Gemini for quick tactical tips, Claude for strategic feedback.

### Custom Workflows

Create your own workflow combining multiple prompts:
1. After each question: "Review Latest"
2. Every 3-4 questions: "Review All Segments"
3. End of interview: "Overall Feedback"

## Technical Details

### Data Storage
- Custom prompts are stored in your browser's **localStorage**
- Storage key: `customPrompts`
- Data format: JSON array of prompt objects
- Each prompt has: `id`, `icon`, `label`, `prompt`

### Persistence
- Prompts persist across overlay restarts
- Prompts persist across system reboots
- **Note**: Private/incognito mode may not save prompts
- Clearing browser data will reset prompts

### Default Prompts
- Default prompts have IDs starting with `default-`
- Custom prompts have IDs like `custom-1732894567890` (timestamp-based)
- Defaults are loaded only on first use
- Reset to Defaults replaces all prompts with the original 5

## Summary

Custom Prompts make it **fast and easy** to get help from Claude Desktop during interviews without typing long prompts. Create your own library of prompts tailored to your interview style and needs!

**Remember:** The goal is to help you perform better, not to give you scripted answers. Use Claude's insights to inform your thinking, then answer in your own words with your own experience.

Good luck with your interviews! 🚀
