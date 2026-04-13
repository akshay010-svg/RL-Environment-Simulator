import asyncio
import httpx
import random
import json

API_BASE_URL = "http://localhost:8000"

async def run_random_agent(episodes=1, max_steps=20):
    """
    Runs a simple random-action agent against the RL environment.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Check health
        try:
            health = await client.get(f"{API_BASE_URL}/health")
            print(f"Health Check: {health.json()}", flush=True)
        except httpx.ConnectError:
            print("Server is not running. Please start it using 'docker-compose up -d' or 'uvicorn app.main:app --reload'", flush=True)
            return

        for episode in range(episodes):
            print(f"\n{'='*50}\nStarting Episode {episode + 1}\n{'='*50}", flush=True)
            
            # Reset environment
            reset_response = await client.post(f"{API_BASE_URL}/rl/reset")
            reset_data = reset_response.json()
            
            episode_id = reset_data["episode_id"]
            observation = reset_data["observation"]
            
            total_reward = 0.0
            done = False
            step = 0
            
            print(f"Initial State | Episode ID: {episode_id}", flush=True)
            print(f"Tickets available: {len(observation['tickets'])}", flush=True)
            print(f"Agents available: {len(observation['users'])}", flush=True)
            
            while not done and step < max_steps:
                step += 1
                
                # Fetch available entities from observation
                tickets = observation["tickets"]
                users = observation["users"]
                
                if not tickets or not users:
                    print("No tickets or users available to take action.", flush=True)
                    break
                
                # We filter tickets that are not resolved for actions
                open_tickets = [t for t in tickets if t["status"] != "resolved"]
                if not open_tickets:
                    print("All tickets seem to be resolved!", flush=True)
                    break

                target_ticket = random.choice(open_tickets)
                
                # Decide on a random valid action based on state
                possible_actions = []
                
                if target_ticket["assignee_id"] is None:
                    # Action: Assign ticket
                    random_user = random.choice(users)
                    possible_actions.append({
                        "action_type": "assign_ticket",
                        "ticket_id": target_ticket["id"],
                        "user_id": random_user["id"]
                    })
                
                if target_ticket["assignee_id"] is not None:
                    # Action: Create Task, Complete Task or Resolve Ticket
                    possible_actions.extend([
                        {
                            "action_type": "create_task",
                            "ticket_id": target_ticket["id"],
                            "task_description": "Investigate logs for errors"
                        },
                        {
                            "action_type": "resolve_ticket",
                            "ticket_id": target_ticket["id"]
                        }
                    ])
                
                # Fallback action just in case 
                if not possible_actions:
                    possible_actions.append({
                        "action_type": "update_priority",
                        "ticket_id": target_ticket["id"],
                        "new_priority": random.choice(["low", "medium", "high"])
                    })
                    
                action_to_take = random.choice(possible_actions)
                
                # Print Action
                print(f"\nStep {step} | Agent attempting Action: {action_to_take['action_type']}", flush=True)
                
                # Take step
                step_payload = {
                    "episode_id": episode_id,
                    "action": action_to_take
                }
                
                step_res = await client.post(f"{API_BASE_URL}/rl/step", json=step_payload)
                step_data = step_res.json()
                
                reward = step_data.get("reward", 0.0)
                done = step_data.get("done", False)
                info = step_data.get("info", {})
                observation = step_data.get("observation", observation)
                
                total_reward += reward
                
                print(f"Info: {info.get('result') or info.get('error')}", flush=True)
                print(f"Reward Received: {reward} | Total Reward: {total_reward:.2f} | Done: {done}", flush=True)

            print(f"\nEpisode {episode + 1} Finished! Total Reward accumulated: {total_reward:.2f}", flush=True)

if __name__ == "__main__":
    asyncio.run(run_random_agent(episodes=1, max_steps=15))
