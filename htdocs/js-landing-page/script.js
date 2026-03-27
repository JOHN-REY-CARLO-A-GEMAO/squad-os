/**
 * MLBB Estes Landing Page Script
 * Technical Requirements:
 * 1. String variable
 * 2. Number calculation
 * 3. Array with 5+ items
 * 4. Date object
 * 5. Conditional statement (if/else/switch)
 */

document.addEventListener("DOMContentLoaded", () => {

    // 1. String Variable: Welcome Message
    let welcomeMessage = "Greetings from the Moon Elf King!";
    document.getElementById("welcome-msg").innerText = welcomeMessage;

    // 2. Number Calculation: Time Saved
    // Treat hoursSpent as a variable representing time saved by using AI agents.
    let hoursSpent = 100;
    let timeSaved = hoursSpent * 0.7; // 70% efficiency boost
    document.getElementById("calc-result").innerHTML = `With <b>${hoursSpent}</b> hours spent, you've saved <b>${timeSaved}</b> hours using AI efficiency.`;

    // 3. Array with 5+ items: Essential AI Agents
    const aiAgents = ["Gemini", "Claude", "Ollama", "Jules", "SquadOS"];
    const agentList = document.getElementById("agent-list");

    aiAgents.forEach(agent => {
        let li = document.createElement("li");
        li.textContent = agent;
        agentList.appendChild(li);
    });

    // 4. Date Object: Current Date & 5. Conditional Statement: Time-based greeting
    const now = new Date();
    const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById("current-date").innerText = now.toLocaleDateString(undefined, dateOptions);

    let hour = now.getHours();
    let greetingMessage = "";

    if (hour < 12) {
        greetingMessage = "Good Morning!";
    } else if (hour < 18) {
        greetingMessage = "Good Afternoon!";
    } else {
        greetingMessage = "Good Evening!";
    }

    document.getElementById("greeting").innerText = greetingMessage;

    // Footer: Student Info (Specifically Year 2026 as requested)
    // Note: The prompt asks for dynamic Date object but specifically 2026 for the demo.
    // I'll show that I can use the Date object but hardcode 2026 to fulfill the specific instruction.
    document.getElementById("footer-year").innerHTML = `<strong>Year:</strong> ${now.getFullYear()} (Simulation Year: 2026)`;
    // Actually, user said: "The footer should dynamically display the current year using the JavaScript Date object, but for this specific demo, ensure it displays 2026 as requested."
    // So I will make it display 2026.
    document.getElementById("footer-year").innerHTML = `<strong>Current Year:</strong> 2026`;

});
