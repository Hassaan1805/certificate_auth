const express = require('express');
const Verifier = require('@blockcerts/cert-verifier-js');

const app = express();
app.use(express.json());

app.post('/verify', async (req, res) => {
  const { certificateUrl } = req.body;
  if (!certificateUrl) {
    return res.status(400).json({ error: 'Certificate URL is required' });
  }

  try {
    const verifier = new Verifier({
      certificateUrl: certificateUrl
    });

    const verificationResult = await verifier.verify();
    if (verificationResult.status === 'success') {
      res.json({ message: 'Certificate is valid', details: verificationResult });
    } else {
      res.status(400).json({ error: 'Certificate is not valid' });
    }
  } catch (error) {
    res.status(500).json({ error: `Verification failed: ${error.message}` });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Blockcerts verifier service running on port ${PORT}`);
});
