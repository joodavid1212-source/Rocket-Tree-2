# Rocket Tree: Sunlight Thief (pixel edition)

An arcade game where you are a flying rocket-ship tree stealing every drop of
rain and every sunbeam from the other trees, while they furiously pelt you with
apples.

The whole game is drawn in code at a tiny 320x224 resolution and scaled up 3x,
which gives it the chunky pixel-art look. There are no image or sound files to
download.

## Run it

```bash
pip install -r requirements.txt
python main.py
```

Requires Python 3.8+.

## Controls

| Key | Action |
| --- | --- |
| Arrow keys / WASD | Fly (uses fuel) |
| P | Pause |
| SPACE / ENTER | Start / restart |
| ESC | Quit |

## How to play

- You have **3 lives** (hearts, top left). Getting hit by an apple costs one life.
- **Points:** 1 point for every raindrop or sunbeam you fly into. The sun dims,
  the clouds shrink and the other trees wither as you steal.
- **Fuel:** your rocket burns fuel whenever you hold a movement key (the fuel
  bar is under the hearts). Hovering in place is free. Catch the **flying fuel
  cans** (they flap across the sky) to refill 40%. If the tank runs dry you
  sink and can only glide sideways. **If you hit the ground, you crash and it's
  an instant game over**, no matter how many lives you have left.
- **Fertilizer:** every so often a bag drops. Grab it for **10 seconds of
  invincibility** with a green aura. Apples are blasted away.
- **Difficulty:** the game gets harder over time. Apples fly faster, more trees
  wake up and throw more often, then falling acorns (18s) and wavy pinecones
  (36s) join in.
- When the game ends, the game over screen shows your points, how you went
  out, and a random comment based on your score. Score under 25 and you get
  insulted; score 50 or more and you get complimented.
