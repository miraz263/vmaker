/* ===============================
   CHARACTER MOTION ENGINE
=============================== */

function evaluateCharacterState(char, t) {
    const state = {
        x: char.initial_state.position.x,
        y: char.initial_state.position.y,
        pose: char.initial_state.pose || "idle",
        emotion: char.initial_state.emotion || "neutral",
        facing: char.initial_state.facing || "right"
    };

    if (!Array.isArray(char.actions)) return state;

    char.actions.forEach(action => {
        if (t < action.at) return;

        switch (action.type) {

            case "walk":
                {
                    const speed = action.speed || 5;
                    const dir = action.direction === "left" ? -1 : 1;
                    state.x += dir * speed * (t - action.at);
                    state.pose = "walk";
                    break;
                }

            case "run":
                {
                    const speed = action.speed || 10;
                    const dir = action.direction === "left" ? -1 : 1;
                    state.x += dir * speed * (t - action.at);
                    state.pose = "run";
                    break;
                }

            case "sit":
                state.pose = "sit";
                break;

            case "idle":
                state.pose = "idle";
                break;

            case "look":
                state.facing = action.direction || "right";
                break;

            case "emotion_change":
                state.emotion = action.emotion;
                break;

            case "think":
                state.pose = "idle";
                state.emotion = "thoughtful";
                break;
        }
    });

    return state;
}