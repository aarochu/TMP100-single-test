# TMP100 Single Sensor Test

Reads the temperature from **one TMP100 sensor** on a Raspberry Pi, over and over,
and prints it to the screen. Use it to check that a sensor is wired up and working
before you build anything bigger with it.

```text
elapsed      temp (C)
---------------------
      0.0s     21.125
      1.0s     21.438
      2.0s     21.625

3 reading(s) over 2.0 s, 0 failed
min 21.125 C   max 21.625 C   mean 21.396 C
```

---

## What you need

- A Raspberry Pi with Raspberry Pi OS on it
- One TMP100 temperature sensor
- 4 jumper wires
- A keyboard and screen for the Pi (or SSH into it)

---

## Step 1 — Turn the Pi OFF

Unplug the power. **Never move wires while the Pi is on.**

---

## Step 2 — Connect 4 wires

Connect the sensor to the Pi's pins like this:

| Sensor pin | Goes to Pi pin | What it is |
| --- | --- | --- |
| V+ (or VCC) | pin **1** | 3.3 volts (power) |
| GND | pin **6** | ground |
| SDA | pin **3** | data |
| SCL | pin **5** | clock |

Pin 1 is the corner pin closest to the SD card slot. Count carefully — the pins are
in two rows, and the odd numbers (1, 3, 5) are all in the same row.

The sensor also has two pins called **ADD0** and **ADD1**. They pick the sensor's
"name" (its address):

- Both connected to GND → the name is `0x48`
- Both connected to 3.3V → the name is `0x4f`

Either is fine. You will find out which one you have in Step 5.

---

## Step 3 — Turn the Pi back on and open a terminal

Plug the power back in, wait for it to start, and open the black terminal window.

---

## Step 4 — Switch on I2C

I2C is the "language" the sensor speaks. The Pi has it switched off at first.

Type this and press Enter:

```bash
sudo raspi-config
```

Then use the arrow keys:

1. Choose **Interface Options**, press Enter
2. Choose **I2C**, press Enter
3. Choose **Yes**, press Enter
4. Press Enter again on "OK"
5. Choose **Finish**

Now restart the Pi:

```bash
sudo reboot
```

Wait for it to come back, and open the terminal again.

---

## Step 5 — Check the Pi can see your sensor

### 5a. Do you already have the tool?

Type this:

```bash
i2cdetect -V
```

- If you see a **version number** (like `i2cdetect version 4.3`), you already have it.
  **Skip to 5b.**
- If you see **`command not found`**, install it first:

  ```bash
  sudo apt install -y i2c-tools
  ```

### 5b. Is I2C actually switched on?

```bash
ls /dev/i2c-*
```

- If you see **`/dev/i2c-1`**, it is on. Carry on to 5c.
- If you see **`No such file or directory`**, Step 4 did not take. Go back and do
  Step 4 again, and make sure you reboot at the end.

### 5c. Look for the sensor

```bash
i2cdetect -y 1
```

You should see a grid of dots with **one number** in it, like this:

```text
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 4f
```

**Write down that number.** It is either `48` or `4f`. That is your sensor's name.

If you only see dots and no number, go to **"If it does not work"** at the bottom.

---

## Step 6 — Download this code

```bash
git clone https://github.com/aarochu/TMP100-single-test.git
cd TMP100-single-test
```

---

## Step 7 — Set it up (only needed once)

Copy and paste these three lines, one at a time:

```bash
sudo apt install -y python3-venv
```

```bash
python3 -m venv .venv && source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

---

## Step 8 — Run it!

If your number in Step 5 was **4f**, type:

```bash
python3 tmp100_read.py
```

If your number was **48**, type this instead:

```bash
python3 tmp100_read.py 1 0 0x48
```

Numbers should start appearing, one every second. **It worked!**

Hold your finger on the sensor and watch the number go up.

---

## Step 9 — Stop it

Hold the **Ctrl** key and press **C**.

You will see a little summary of the highest, lowest, and average temperature.

---

## Doing more

The command takes up to three extra numbers:

```bash
python3 tmp100_read.py                # one reading every second, forever
python3 tmp100_read.py 0.5            # one reading every half second
python3 tmp100_read.py 0.5 60         # every half second, stop after 60 seconds
python3 tmp100_read.py 0.5 60 0x48    # ...and use the sensor named 0x48
```

Next time you come back, you only need to `cd` into the folder, then:

```bash
source .venv/bin/activate
python3 tmp100_read.py
```

---

## If it does not work

| What you see | What to do |
| --- | --- |
| `i2cdetect` shows only dots | Turn the Pi off and check all 4 wires are in the right pins. A loose wire is the most common problem. |
| `No TMP100 answered at 0x4f` | Your sensor is probably named `0x48`. Run `python3 tmp100_read.py 1 0 0x48` instead. |
| `command not found: i2cdetect` | Run `sudo apt install -y i2c-tools` first. |
| `ModuleNotFoundError: smbus2` | You forgot `source .venv/bin/activate`. Run it, then try again. |
| Some rows say `ERR` | The sensor answered sometimes but not always. This almost always means a loose wire. |
| The number never changes | That is normal — room temperature is steady. Hold your finger on the sensor and watch it rise. |

---

## For developers

Run the tests. No Raspberry Pi and no sensor needed — a fake sensor stands in:

```bash
python3 -m unittest discover -s tests -v
```

Run the same tests inside Debian 12 (the OS that Raspberry Pi OS is built on), which
also checks that the install instructions above actually work:

```bash
docker build -t tmp100-test . && docker run --rm tmp100-test
```

### How the reading works

The TMP100 returns 2 bytes. The temperature is the top 12 bits, left-justified, in
two's complement. The script shifts them down, handles the negative case, and
multiplies by 0.0625 °C per count:

```python
temp = ((data[0] << 8) + (data[1] & 0b11110000)) >> 4
if temp > 2047:
    temp -= 4096
return temp * 0.0625
```

Before reading, it writes `0b1100000` to the config register to select 12-bit
resolution (0.0625 °C per step instead of the default 0.5 °C), then waits 320 ms for
the first conversion to finish.
