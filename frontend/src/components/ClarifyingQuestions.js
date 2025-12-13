/**
 * ClarifyingQuestions - Full-screen card-based question UI
 *
 * Shows questions one at a time with smooth transitions.
 * Supports multiple_choice, short_text, and yes_no question types.
 * Includes Skip / Skip All buttons and interrupt banner when processing completes.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { tokens } from '../design-system';
import { Button, Card, Text, Progress, Input } from '../design-system';
import { CheckCircleIcon, ArrowRightIcon } from '@heroicons/react/24/outline';

const ClarifyingQuestions = ({
  questions = [],
  onAnswer,
  onSkip,
  onSkipAll,
  onComplete,
  isProcessingComplete = false,
  taskStatus = 'processing',
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [selectedOption, setSelectedOption] = useState(null);
  const [textInput, setTextInput] = useState('');
  const [showInterruptBanner, setShowInterruptBanner] = useState(false);
  const [redirectCountdown, setRedirectCountdown] = useState(3);
  const [integrationFeedback, setIntegrationFeedback] = useState(null);

  const currentQuestion = questions[currentIndex];
  const progress = ((currentIndex) / questions.length) * 100;
  const isLastQuestion = currentIndex >= questions.length - 1;

  // Handle processing complete - show interrupt banner
  useEffect(() => {
    if (isProcessingComplete && currentIndex < questions.length) {
      setShowInterruptBanner(true);
    }
  }, [isProcessingComplete, currentIndex, questions.length]);

  // Countdown for auto-redirect
  useEffect(() => {
    if (!showInterruptBanner) return;

    const timer = setInterval(() => {
      setRedirectCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          onComplete?.(answers);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [showInterruptBanner, answers, onComplete]);

  const handleSubmitAnswer = useCallback(async () => {
    if (!currentQuestion) return;

    let answer;
    if (currentQuestion.type === 'multiple_choice') {
      answer = selectedOption;
    } else if (currentQuestion.type === 'yes_no') {
      answer = selectedOption;
    } else {
      answer = textInput;
    }

    if (answer === null || answer === undefined || answer === '') return;

    const newAnswers = { ...answers, [currentQuestion.id]: answer };
    setAnswers(newAnswers);

    // Submit answer to backend and get integration feedback
    try {
      const response = await onAnswer?.(currentQuestion.id, answer);
      if (response?.integration_status) {
        setIntegrationFeedback({
          status: response.integration_status,
          message: response.message
        });
        // Clear feedback after 3 seconds
        setTimeout(() => setIntegrationFeedback(null), 3000);
      }
    } catch (error) {
      console.error('Failed to submit answer:', error);
    }

    // Move to next question or complete
    if (isLastQuestion) {
      onComplete?.(newAnswers);
    } else {
      setCurrentIndex(prev => prev + 1);
      setSelectedOption(null);
      setTextInput('');
    }
  }, [currentQuestion, selectedOption, textInput, answers, isLastQuestion, onAnswer, onComplete]);

  const handleSkip = useCallback(() => {
    onSkip?.(currentQuestion?.id);

    if (isLastQuestion) {
      onComplete?.(answers);
    } else {
      setCurrentIndex(prev => prev + 1);
      setSelectedOption(null);
      setTextInput('');
    }
  }, [currentQuestion, isLastQuestion, answers, onSkip, onComplete]);

  const handleSkipAll = useCallback(() => {
    onSkipAll?.();
    onComplete?.(answers);
  }, [answers, onSkipAll, onComplete]);

  const handleViewResults = useCallback(() => {
    onComplete?.(answers);
  }, [answers, onComplete]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        if (currentQuestion?.type !== 'short_text' || textInput.trim()) {
          handleSubmitAnswer();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSubmitAnswer, currentQuestion, textInput]);

  if (!currentQuestion) {
    return null;
  }

  const getCategoryColor = (category) => {
    const colors = {
      scale: tokens.colors.info[500],
      users: tokens.colors.success[500],
      integrations: tokens.colors.warning[500],
      constraints: tokens.colors.error[500],
      tech: tokens.colors.secondary[500],
      features: tokens.colors.primary[500],
    };
    return colors[category] || tokens.colors.neutral[500];
  };

  const getImportanceBadge = (importance) => {
    const styles = {
      high: { bg: tokens.colors.error[500] + '30', color: tokens.colors.error[500] },
      medium: { bg: tokens.colors.warning[500] + '30', color: tokens.colors.warning[500] },
      low: { bg: tokens.colors.neutral[400] + '30', color: tokens.colors.neutral[400] },
    };
    return styles[importance] || styles.medium;
  };

  return (
    <div style={styles.container}>
      {/* Interrupt Banner */}
      {showInterruptBanner && (
        <div style={styles.interruptBanner}>
          <div style={styles.interruptContent}>
            <CheckCircleIcon style={styles.interruptIcon} />
            <div>
              <Text style={styles.interruptTitle}>Your project is ready!</Text>
              <Text style={styles.interruptSubtitle}>
                Redirecting in {redirectCountdown} seconds...
              </Text>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={handleViewResults}
            >
              View Results Now
            </Button>
          </div>
        </div>
      )}

      {/* Progress */}
      <div style={styles.progressContainer}>
        <Text style={styles.progressText}>
          Question {currentIndex + 1} of {questions.length}
        </Text>
        <Progress
          value={progress}
          max={100}
          size="sm"
          variant="primary"
          style={{ maxWidth: '200px' }}
        />
      </div>

      {/* Question Card */}
      <div style={styles.cardWrapper}>
        <Card style={styles.questionCard} variant="elevated">
          {/* Category & Importance */}
          <div style={styles.metaRow}>
            <span
              style={{
                ...styles.categoryBadge,
                backgroundColor: getCategoryColor(currentQuestion.category) + '20',
                color: getCategoryColor(currentQuestion.category),
              }}
            >
              {currentQuestion.category}
            </span>
            <span
              style={{
                ...styles.importanceBadge,
                backgroundColor: getImportanceBadge(currentQuestion.importance).bg,
                color: getImportanceBadge(currentQuestion.importance).color,
              }}
            >
              {currentQuestion.importance}
            </span>
          </div>

          {/* Question Text */}
          <Text style={styles.questionText}>
            {currentQuestion.question}
          </Text>

          {/* Answer Input */}
          <div style={styles.answerSection}>
            {currentQuestion.type === 'multiple_choice' && (
              <div style={styles.optionsGrid}>
                {currentQuestion.options?.map((option, index) => (
                  <button
                    key={index}
                    onClick={() => setSelectedOption(option)}
                    style={{
                      ...styles.optionButton,
                      ...(selectedOption === option ? styles.optionButtonSelected : {}),
                    }}
                  >
                    <span style={styles.optionRadio}>
                      {selectedOption === option ? (
                        <span style={styles.optionRadioSelected} />
                      ) : null}
                    </span>
                    <span>{option}</span>
                  </button>
                ))}
              </div>
            )}

            {currentQuestion.type === 'yes_no' && (
              <div style={styles.yesNoContainer}>
                <button
                  onClick={() => setSelectedOption('yes')}
                  style={{
                    ...styles.yesNoButton,
                    ...(selectedOption === 'yes' ? styles.yesNoButtonSelected : {}),
                  }}
                >
                  Yes
                </button>
                <button
                  onClick={() => setSelectedOption('no')}
                  style={{
                    ...styles.yesNoButton,
                    ...(selectedOption === 'no' ? styles.yesNoButtonSelected : {}),
                  }}
                >
                  No
                </button>
              </div>
            )}

            {currentQuestion.type === 'short_text' && (
              <Input
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Type your answer..."
                style={styles.textInput}
              />
            )}
          </div>

          {/* Action Buttons */}
          <div style={styles.actionRow}>
            <div style={styles.skipButtons}>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSkip}
              >
                Skip
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSkipAll}
                style={styles.skipAllButton}
              >
                Skip All
              </Button>
            </div>
            <Button
              variant="primary"
              onClick={handleSubmitAnswer}
              disabled={
                (currentQuestion.type === 'multiple_choice' && !selectedOption) ||
                (currentQuestion.type === 'yes_no' && !selectedOption) ||
                (currentQuestion.type === 'short_text' && !textInput.trim())
              }
              icon={isLastQuestion ? CheckCircleIcon : ArrowRightIcon}
              iconPosition="right"
            >
              {isLastQuestion ? 'Finish' : 'Next'}
            </Button>
          </div>
        </Card>
      </div>

      {/* Integration feedback toast */}
      {integrationFeedback && (
        <div style={{
          ...styles.integrationFeedback,
          ...(integrationFeedback.status === 'will_integrate' ? styles.feedbackWillIntegrate : {}),
          ...(integrationFeedback.status === 'already_integrated' ? styles.feedbackAlreadyIntegrated : {}),
          ...(integrationFeedback.status === 'stored' ? styles.feedbackStored : {}),
        }}>
          <Text style={styles.feedbackText}>
            {integrationFeedback.message}
          </Text>
        </div>
      )}

      {/* Background processing indicator */}
      {!isProcessingComplete && taskStatus === 'processing' && (
        <div style={styles.processingIndicator}>
          <div style={styles.processingDot} />
          <Text style={styles.processingText}>
            Analyzing your project in the background...
          </Text>
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    position: 'relative',
    width: '100%',
    minHeight: '500px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: tokens.spacing[6],
  },

  interruptBanner: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    backgroundColor: tokens.colors.success[500],
    padding: tokens.spacing[4],
    zIndex: tokens.zIndex.banner,
  },

  interruptContent: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: tokens.spacing[4],
    maxWidth: '800px',
    margin: '0 auto',
  },

  interruptIcon: {
    width: '32px',
    height: '32px',
    color: 'white',
  },

  interruptTitle: {
    color: 'white',
    fontWeight: tokens.typography.fontWeight.semibold,
    fontSize: tokens.typography.fontSize.lg[0],
    margin: 0,
  },

  interruptSubtitle: {
    color: 'rgba(255, 255, 255, 0.9)',
    fontSize: tokens.typography.fontSize.sm[0],
    margin: 0,
  },

  progressContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[6],
  },

  progressText: {
    color: tokens.colors.dark.muted,
    fontSize: tokens.typography.fontSize.sm[0],
  },

  cardWrapper: {
    width: '100%',
    maxWidth: '600px',
  },

  questionCard: {
    padding: tokens.spacing[8],
  },

  metaRow: {
    display: 'flex',
    gap: tokens.spacing[2],
    marginBottom: tokens.spacing[4],
  },

  categoryBadge: {
    padding: `${tokens.spacing[1]} ${tokens.spacing[3]}`,
    borderRadius: tokens.borderRadius.full,
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.medium,
    textTransform: 'capitalize',
  },

  importanceBadge: {
    padding: `${tokens.spacing[1]} ${tokens.spacing[3]}`,
    borderRadius: tokens.borderRadius.full,
    fontSize: tokens.typography.fontSize.xs[0],
    fontWeight: tokens.typography.fontWeight.medium,
    textTransform: 'capitalize',
  },

  questionText: {
    fontSize: tokens.typography.fontSize['2xl'][0],
    fontWeight: tokens.typography.fontWeight.semibold,
    color: tokens.colors.dark.text,
    marginBottom: tokens.spacing[6],
    lineHeight: tokens.typography.lineHeight.relaxed,
  },

  answerSection: {
    marginBottom: tokens.spacing[6],
  },

  optionsGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacing[3],
  },

  optionButton: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[3],
    padding: tokens.spacing[4],
    backgroundColor: 'transparent',
    border: `1px solid ${tokens.colors.dark.border}`,
    borderRadius: tokens.borderRadius.lg,
    color: tokens.colors.dark.text,
    fontSize: tokens.typography.fontSize.base[0],
    textAlign: 'left',
    cursor: 'pointer',
    transition: tokens.transitions.all,
  },

  optionButtonSelected: {
    borderColor: tokens.colors.primary[500],
    backgroundColor: tokens.colors.primary[500] + '15',
  },

  optionRadio: {
    width: '20px',
    height: '20px',
    borderRadius: tokens.borderRadius.full,
    border: `2px solid ${tokens.colors.dark.border}`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },

  optionRadioSelected: {
    width: '10px',
    height: '10px',
    borderRadius: tokens.borderRadius.full,
    backgroundColor: tokens.colors.primary[500],
  },

  yesNoContainer: {
    display: 'flex',
    gap: tokens.spacing[4],
  },

  yesNoButton: {
    flex: 1,
    padding: tokens.spacing[4],
    backgroundColor: 'transparent',
    border: `1px solid ${tokens.colors.dark.border}`,
    borderRadius: tokens.borderRadius.lg,
    color: tokens.colors.dark.text,
    fontSize: tokens.typography.fontSize.lg[0],
    fontWeight: tokens.typography.fontWeight.medium,
    cursor: 'pointer',
    transition: tokens.transitions.all,
  },

  yesNoButtonSelected: {
    borderColor: tokens.colors.primary[500],
    backgroundColor: tokens.colors.primary[500] + '15',
  },

  textInput: {
    width: '100%',
  },

  actionRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: tokens.spacing[4],
    borderTop: `1px solid ${tokens.colors.dark.border}`,
  },

  skipButtons: {
    display: 'flex',
    gap: tokens.spacing[2],
  },

  skipAllButton: {
    color: tokens.colors.dark.muted,
  },

  processingIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacing[2],
    padding: `${tokens.spacing[2]} ${tokens.spacing[4]}`,
    backgroundColor: tokens.colors.dark.surface,
    borderRadius: tokens.borderRadius.full,
    border: `1px solid ${tokens.colors.dark.border}`,
    marginTop: tokens.spacing[6],
  },

  processingDot: {
    width: '8px',
    height: '8px',
    borderRadius: tokens.borderRadius.full,
    backgroundColor: tokens.colors.info[500],
    animation: 'pulse 2s ease-in-out infinite',
  },

  processingText: {
    color: tokens.colors.dark.muted,
    fontSize: tokens.typography.fontSize.sm[0],
  },

  integrationFeedback: {
    position: 'absolute',
    bottom: tokens.spacing[16],
    left: '50%',
    transform: 'translateX(-50%)',
    padding: `${tokens.spacing[3]} ${tokens.spacing[5]}`,
    borderRadius: tokens.borderRadius.lg,
    animation: 'fadeInOut 3s ease-in-out',
  },

  feedbackWillIntegrate: {
    backgroundColor: tokens.colors.success[500] + '20',
    border: `1px solid ${tokens.colors.success[500]}`,
  },

  feedbackAlreadyIntegrated: {
    backgroundColor: tokens.colors.info[500] + '20',
    border: `1px solid ${tokens.colors.info[500]}`,
  },

  feedbackStored: {
    backgroundColor: tokens.colors.warning[500] + '20',
    border: `1px solid ${tokens.colors.warning[500]}`,
  },

  feedbackText: {
    color: tokens.colors.dark.text,
    fontSize: tokens.typography.fontSize.sm[0],
    fontWeight: tokens.typography.fontWeight.medium,
  },
};

// Add CSS animations
const styleSheet = document.createElement('style');
styleSheet.textContent = `
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  @keyframes fadeInOut {
    0% { opacity: 0; transform: translateX(-50%) translateY(10px); }
    15% { opacity: 1; transform: translateX(-50%) translateY(0); }
    85% { opacity: 1; transform: translateX(-50%) translateY(0); }
    100% { opacity: 0; transform: translateX(-50%) translateY(-10px); }
  }
`;
if (typeof document !== 'undefined' && !document.getElementById('clarifying-questions-styles')) {
  styleSheet.id = 'clarifying-questions-styles';
  document.head.appendChild(styleSheet);
}

export default ClarifyingQuestions;
