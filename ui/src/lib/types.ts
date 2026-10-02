export type QuestionType = 'choice' | 'noul';

export interface Question {
	type: QuestionType;
	instructions: string;
	/** choice only: label → description */
	criteria?: Record<string, string>;
}

/** What the user asked: a question, and the options to choose from (none means yes or no). */
export interface Ask {
	question: string;
	options: string[];
}

export interface ChoiceAnswer {
	type: 'choice';
	choice: string;
	confidence: number;
	probabilities: Record<string, number>;
}

export interface NoulAnswer {
	type: 'noul';
	noul: number;
}

export interface OtherAnswer {
	type: string;
	confidence?: number;
	[key: string]: unknown;
}

export type Answer = ChoiceAnswer | NoulAnswer | OtherAnswer;

export interface Evidence {
	title: string;
	url: string;
	content: string;
	query: string;
}

export interface QuestionReport {
	initial_confidence: number;
	confidence: number;
	searched: boolean;
	rounds: number;
	query: string | null;
	needs_review: boolean;
}

export interface SearchReport {
	threshold: number;
	rounds: number;
	stopped: string | null;
	questions: Record<string, QuestionReport>;
	evidence: Evidence[];
	unresponsive_engines: string[];
}

export interface SystemOneResponse {
	model: string;
	answers: Record<string, Answer>;
	usage?: Record<string, number>;
	latency_ms?: number;
	search?: SearchReport;
}

export interface UserMessage extends Ask {
	id: string;
	role: 'user';
}

export interface AssistantMessage {
	id: string;
	role: 'assistant';
	ask: Ask;
	webSearch: boolean;
	status: 'pending' | 'done' | 'error';
	response?: SystemOneResponse;
	error?: string;
	elapsedMs?: number;
}

export type Message = UserMessage | AssistantMessage;

export interface Chat {
	id: string;
	title: string;
	createdAt: number;
	messages: Message[];
}
