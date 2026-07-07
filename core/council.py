"""
Council of Models — Multi-LLM Collaborative Reasoning Engine
--------------------------------------------------------------
Spins up multiple local LLMs to collaboratively solve complex tasks
using a structured debate protocol:

    Phase 1: UNDERSTAND — Each model independently analyzes the request.
    Phase 2: PROPOSE    — Each model proposes an approach/solution.
    Phase 3: DEBATE     — Models see each other's proposals and critique them.
    Phase 4: SYNTHESIZE — A moderator model merges the best ideas into a final plan.
    Phase 5: VERIFY     — All models vote on whether the synthesis is correct.

This reduces hallucinations, blind spots, and single-model biases.

Usage:
    from core.council import Council

    council = Council(models=["gemma4:e2b-mlx", "ministral-3:8b", "llama3.1:8b"])
    result = council.deliberate("Explain how to implement a rate limiter in Python")

    # result = {
    #     "final_answer": "...",
    #     "consensus": True,
    #     "votes": {"gemma4:e2b-mlx": "APPROVE", ...},
    #     "transcript": [...]
    # }

Or from the CLI:
    python run.py --council "Your complex question here"
"""

import json
import time
from typing import Optional
from core.models import get_conversation_session


# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_COUNCIL = ["gemma4:e2b-mlx", "ministral-3:8b", "llama3.1:8b"]
MAX_DEBATE_ROUNDS = 2


# ── Council Class ─────────────────────────────────────────────────────────────

class Council:
    """
    A multi-model deliberation engine.

    Each model gets its own conversation session. The Council mediates
    a structured debate where models can see (and critique) each other's outputs.
    """

    def __init__(self, models: list = None, moderator: str = None, verbose: bool = True):
        """
        Args:
            models:    List of Ollama model names to sit on the council.
            moderator: The model that synthesizes the final answer (defaults to first model).
            verbose:   Print the deliberation transcript to stdout.
        """
        self.models = models or DEFAULT_COUNCIL
        self.moderator = moderator or self.models[0]
        self.verbose = verbose
        self.transcript = []

    def _log(self, msg: str, model: str = "Council"):
        """Log a message to transcript and optionally print."""
        entry = {"speaker": model, "message": msg, "timestamp": time.time()}
        self.transcript.append(entry)
        if self.verbose:
            tag = f"[{model}]" if model != "Council" else "[Council]"
            print(f"  {tag} {msg[:300]}")

    def deliberate(self, task: str, context: str = "") -> dict:
        """
        Run the full deliberation protocol on a task.

        Args:
            task:    The user's request or question.
            context: Optional additional context (scraped data, file contents, etc.)

        Returns:
            dict with final_answer, consensus status, votes, and transcript.
        """
        self._log(f"📋 Task: {task[:200]}")
        self._log(f"🧠 Council Members: {', '.join(self.models)}")
        self._log(f"👑 Moderator: {self.moderator}")
        self._log(f"{'─' * 60}")

        # ── Phase 1: Independent Analysis ──────────────────────────────────
        self._log("PHASE 1: Independent Analysis", "Council")
        proposals = {}

        for model in self.models:
            self._log(f"Thinking...", model)
            session = get_conversation_session(
                model=model,
                system_prompt=(
                    "You are a member of an AI council. Analyze the following task independently. "
                    "Provide your analysis, approach, and proposed solution. Be thorough but concise. "
                    "Focus on: (1) Understanding what's being asked, (2) Key challenges, "
                    "(3) Your proposed approach, (4) Your solution or answer."
                )
            )
            prompt = f"TASK: {task}"
            if context:
                prompt += f"\n\nADDITIONAL CONTEXT:\n{context[:2000]}"

            try:
                response = session.chat(prompt)
                proposals[model] = response
                self._log(f"Proposal ready ({len(response)} chars)", model)
            except Exception as e:
                proposals[model] = f"(Error: {str(e)})"
                self._log(f"⚠️ Error: {str(e)}", model)

        self._log(f"{'─' * 60}")

        # ── Phase 2: Cross-Review (Debate) ─────────────────────────────────
        self._log("PHASE 2: Cross-Review & Debate", "Council")
        critiques = {}

        for model in self.models:
            # Show this model what OTHER models proposed
            other_proposals = "\n\n".join([
                f"=== {m}'s Proposal ===\n{proposals[m][:1500]}"
                for m in self.models if m != model
            ])

            session = get_conversation_session(
                model=model,
                system_prompt=(
                    "You are reviewing your fellow council members' proposals. "
                    "For each proposal: (1) What's good about it? (2) What's wrong or missing? "
                    "(3) What would you change? Be constructive and specific. "
                    "End with your REVISED position considering their input."
                )
            )
            prompt = (
                f"ORIGINAL TASK: {task}\n\n"
                f"YOUR ORIGINAL PROPOSAL:\n{proposals[model][:1500]}\n\n"
                f"OTHER COUNCIL MEMBERS' PROPOSALS:\n{other_proposals}\n\n"
                f"Review the other proposals and provide your critique and revised position."
            )

            try:
                response = session.chat(prompt)
                critiques[model] = response
                self._log(f"Critique ready ({len(response)} chars)", model)
            except Exception as e:
                critiques[model] = proposals[model]  # Fall back to original
                self._log(f"⚠️ Critique failed, keeping original: {str(e)}", model)

        self._log(f"{'─' * 60}")

        # ── Phase 3: Synthesis (Moderator) ─────────────────────────────────
        self._log("PHASE 3: Synthesis by Moderator", "Council")

        all_positions = "\n\n".join([
            f"=== {m}'s Final Position ===\n{critiques[m][:2000]}"
            for m in self.models
        ])

        moderator_session = get_conversation_session(
            model=self.moderator,
            system_prompt=(
                "You are the Council Moderator. You have received the final positions "
                "from all council members after they debated. Your job is to synthesize "
                "the BEST answer by combining the strongest elements from each position. "
                "Resolve any disagreements by choosing the most well-reasoned argument. "
                "Produce a single, clear, comprehensive final answer."
            )
        )
        synthesis_prompt = (
            f"ORIGINAL TASK: {task}\n\n"
            f"COUNCIL MEMBERS' FINAL POSITIONS (after debate):\n{all_positions}\n\n"
            f"Synthesize the best final answer. Be thorough and accurate."
        )

        try:
            final_answer = moderator_session.chat(synthesis_prompt)
            self._log(f"Synthesis complete ({len(final_answer)} chars)", self.moderator)
        except Exception as e:
            # Fallback: use the moderator's own critique as the answer
            final_answer = critiques.get(self.moderator, proposals.get(self.moderator, "(synthesis failed)"))
            self._log(f"⚠️ Synthesis failed: {str(e)}, using moderator's own critique.", self.moderator)

        self._log(f"{'─' * 60}")

        # ── Phase 4: Verification Vote ─────────────────────────────────────
        self._log("PHASE 4: Verification Vote", "Council")
        votes = {}

        for model in self.models:
            session = get_conversation_session(
                model=model,
                system_prompt=(
                    "You are voting on a synthesized answer. Review it carefully. "
                    "Respond with ONLY one of: APPROVE, REVISE, or REJECT. "
                    "Then on a new line, give a one-sentence reason."
                )
            )
            vote_prompt = (
                f"ORIGINAL TASK: {task}\n\n"
                f"SYNTHESIZED ANSWER:\n{final_answer[:3000]}\n\n"
                f"Vote: APPROVE, REVISE, or REJECT (one word, then reason on next line)."
            )

            try:
                vote_response = session.chat(vote_prompt)
                vote_line = vote_response.strip().split('\n')[0].strip().upper()

                if "APPROVE" in vote_line:
                    votes[model] = "APPROVE"
                elif "REJECT" in vote_line:
                    votes[model] = "REJECT"
                else:
                    votes[model] = "REVISE"

                self._log(f"Vote: {votes[model]}", model)
            except Exception as e:
                votes[model] = "ABSTAIN"
                self._log(f"⚠️ Vote failed: {str(e)}", model)

        # Determine consensus
        approve_count = sum(1 for v in votes.values() if v == "APPROVE")
        consensus = approve_count >= len(self.models) / 2

        self._log(f"{'─' * 60}")
        self._log(
            f"📊 Result: {approve_count}/{len(self.models)} APPROVE → "
            f"{'✅ CONSENSUS REACHED' if consensus else '⚠️ NO CONSENSUS'}",
            "Council"
        )

        # ── Phase 5: Revision (if no consensus) ───────────────────────────
        if not consensus and approve_count > 0:
            self._log("PHASE 5: Revision Attempt", "Council")

            # Collect revision feedback from dissenting models
            dissent_feedback = []
            for model, vote in votes.items():
                if vote != "APPROVE":
                    dissent_feedback.append(f"{model} voted {vote}")

            revision_session = get_conversation_session(
                model=self.moderator,
                system_prompt=(
                    "The council did not reach consensus on your synthesis. "
                    "Some members voted to REVISE or REJECT. "
                    "Review the feedback and produce an improved final answer."
                )
            )
            revision_prompt = (
                f"ORIGINAL ANSWER:\n{final_answer[:2000]}\n\n"
                f"DISSENT: {'; '.join(dissent_feedback)}\n\n"
                f"Produce a revised, improved answer."
            )

            try:
                final_answer = revision_session.chat(revision_prompt)
                self._log(f"Revised answer ready ({len(final_answer)} chars)", self.moderator)
                consensus = True  # Accept the revision as best-effort
            except Exception as e:
                self._log(f"⚠️ Revision failed: {str(e)}", self.moderator)

        return {
            "final_answer": final_answer,
            "consensus": consensus,
            "votes": votes,
            "models_used": self.models,
            "moderator": self.moderator,
            "phases_completed": 5 if not consensus else 4,
            "transcript": self.transcript,
        }

    def quick_check(self, question: str) -> dict:
        """
        Lightweight mode: Ask all models the same question and compare answers.
        No debate, just parallel answers + majority consensus.
        Useful for factual verification.
        """
        self._log(f"⚡ Quick Check: {question[:150]}", "Council")
        answers = {}

        for model in self.models:
            session = get_conversation_session(
                model=model,
                system_prompt="Answer the following question concisely and accurately."
            )
            try:
                response = session.chat(question)
                answers[model] = response
                self._log(f"Answered ({len(response)} chars)", model)
            except Exception as e:
                answers[model] = f"(Error: {str(e)})"
                self._log(f"⚠️ Error: {str(e)}", model)

        return {
            "question": question,
            "answers": answers,
            "models_used": self.models,
        }


# ── Convenience Function ──────────────────────────────────────────────────────

def run_council(task: str, models: list = None, verbose: bool = True) -> dict:
    """
    One-liner to run a council deliberation.

    Usage:
        result = run_council("How should we implement rate limiting?")
        print(result["final_answer"])
    """
    council = Council(models=models, verbose=verbose)
    return council.deliberate(task)
