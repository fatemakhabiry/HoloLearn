import asyncio
import httpx

# ── Config ────────────────────────────────────────────────────────
BASE_URL   = "http://localhost:8000/api/v1"
NUM_TEACHERS = 3  # how many concurrent teachers to simulate

# Put real JWT tokens for different teacher accounts here
# Get them by logging in via /auth/login for each teacher
TEACHER_TOKENS = [
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJFTG9tZGFAZ21haWwuY29tIiwiZXhwIjoxNzc4Njg1MjQwfQ.jqvilNSYMi_5uYR6TswhE4BQFFOMeEDNumzlafQZW-U",  # teacher 1 token
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZWFjaGVyMkBob2xvbGVhcm4uY29tIiwiZXhwIjoxNzc4Njg1Mjg3fQ.bthRt4FJnzvWNrnvPqEIT1_KZyJA3jD3DzlPvrvg370",  # teacher 2 token
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYXRlbWFraGFiaXJ5ODhAZ21haWwuY29tIiwiZXhwIjoxNzc4Njg1MzQyfQ.k4JxqJ7KGaMjTp2NUKtDi2exRpdTYyZeDxObczhGlEQ",  # teacher 3 token
]

# A real uploaded resource file_path for each teacher
# Run POST /sessions/upload-resource first for each teacher
# and paste the returned file_path here
RESOURCE_PATHS = [
    "C:\\Users\\Fatma PC\\HoloLearn\\uploads\\resources\\2\\d0b00b82cdc24fbb8255eaebc613b659.pdf",
    "C:\\Users\\Fatma PC\\HoloLearn\\uploads\\resources\\4\\3950ff2341364aa98a02abcd9b123206.pdf",
    "C:\\Users\\Fatma PC\\HoloLearn\\uploads\\resources\\5\\e1acc7c501314fe0abb46dcdd05b881b.pdf",
]


async def start_session(teacher_index: int, token: str, resource_path: str):
    """Simulate one teacher starting a generation session."""
    headers = {"Authorization": f"Bearer {token}"}

    COURSE_CODES = ["AI101", "FSK201", "DB101"]  # ← put your real ones here


    body = {
        "title":       f"Test Lecture Teacher {teacher_index + 1}",
        "course_code": COURSE_CODES[teacher_index],
        "resources": [
            {
                "resource_type": "PDF",
                "file_path":     resource_path,
                "query":         "summarize the main topics",
            }
        ],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        print(f"[Teacher {teacher_index + 1}] sending start request...")
        try:
            r = await client.post(
                f"{BASE_URL}/session/start",
                json=body,
                headers=headers,
            )
            if r.status_code == 200:
                data = r.json()
                print(
                    f"[Teacher {teacher_index + 1}] ✓ started — "
                    f"session_id={data['session_id']} "
                    f"lecture_id={data['lecture_id']}"
                )
                return data
            else:
                print(f"[Teacher {teacher_index + 1}] ✗ failed — {r.status_code}: {r.text}")
                return None
        except Exception as e:
            print(f"[Teacher {teacher_index + 1}] ✗ error — {e}")
            return None


async def poll_status(teacher_index: int, session_id: int, token: str):
    """Poll status every 30 seconds for up to 10 minutes."""
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for _ in range(20):  # 20 polls × 30 seconds = 10 minutes max
            await asyncio.sleep(30)
            try:
                r = await client.get(
                    f"{BASE_URL}/session/{session_id}/status",
                    headers=headers,
                )
                if r.status_code == 200:
                    data = r.json()
                    step = data["current_step"]
                    pct  = data["progress_percent"]
                    print(
                        f"[Teacher {teacher_index + 1}] "
                        f"session {session_id} → {step} ({pct}%)"
                    )
                    if step in ("done", "failed", "awaiting_approval"):
                        print(f"[Teacher {teacher_index + 1}] reached terminal/pause: {step}")
                        return
            except Exception as e:
                print(f"[Teacher {teacher_index + 1}] poll error: {e}")


async def main():
    print(f"\n{'='*50}")
    print(f"Starting {NUM_TEACHERS} concurrent teacher sessions")
    print(f"{'='*50}\n")

    # ── Step 1: start all sessions at the same time ───────────────
    start_tasks = [
        start_session(i, TEACHER_TOKENS[i], RESOURCE_PATHS[i])
        for i in range(NUM_TEACHERS)
    ]
    results = await asyncio.gather(*start_tasks)

    print(f"\n{'='*50}")
    print("All sessions started — now polling status")
    print(f"{'='*50}\n")

    # ── Step 2: poll all sessions concurrently ────────────────────
    poll_tasks = []
    for i, result in enumerate(results):
        if result:
            poll_tasks.append(
                poll_status(i, result["session_id"], TEACHER_TOKENS[i])
            )

    await asyncio.gather(*poll_tasks)

    print(f"\n{'='*50}")
    print("Test complete")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    asyncio.run(main())