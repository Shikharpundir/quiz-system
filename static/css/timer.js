let timeLeft = 60; // seconds (change as needed)

function startTimer() {
    const timerDisplay = document.getElementById("timer");

    const interval = setInterval(() => {

        let minutes = Math.floor(timeLeft / 60);
        let seconds = timeLeft % 60;

        timerDisplay.innerHTML = 
            minutes + ":" + (seconds < 10 ? "0" : "") + seconds;

        timeLeft--;

        if (timeLeft < 0) {
            clearInterval(interval);
            alert("Time's up! Submitting quiz...");
            document.getElementById("quizForm").submit();
        }

    }, 1000);
}

window.onload = startTimer;